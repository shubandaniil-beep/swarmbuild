"""Phase Orchestrator: runs the swarm through all phases (spec §7.6, §10)."""
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..lib.output_filter import sanitize
from ..models import Agent, Artifact, Issue, Project, ProjectPhase
from . import budget_engine
from .agent_runner import run_agent
from .artifact_packager import package
from .event_log import log_event
from .model_pool import select_pool
from .project_intake import workspace_path
from .release_policy import evaluate
from .role_rotation import build_rotation_plan
from .sandbox_runner import run_command
from .settings_service import get_setting

# where each mandate's output lands on the blackboard, per phase
PHASE_OUTPUT_FILES: dict[str, dict[str, str]] = {
    "swarm_understanding": {"lead": "spec/understanding-summary.md",
                            "builder": "spec/assumptions.md", "critic": "spec/scope.md"},
    "spec_war": {"lead": "spec/technical-spec.md", "critic": "spec/business-spec.md",
                 "judge": "spec/acceptance-criteria.md"},
    "architecture_battle": {"lead": "architecture/architecture.md",
                            "builder": "architecture/architecture-options.md",
                            "critic": "architecture/risks.md"},
    "build_sprint": {"lead": "repo/implementation-log.md"},
    "review_stop": {"reviewer": "reviews/review-report.md"},
    "repair_sprint": {"repairer": "reviews/repair-log.md"},
    "final_audit": {"judge": "reviews/final-audit.md"},
}


def _now():
    return datetime.now(UTC)


def _provider_blocked(exc: Exception | str) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in (
        "no usable real api keys",
        "no usable api keys",
        "all usable keys failed",
        "too many requests",
        "rate limit",
        "rate_limit",
        "quota",
        "resourceexhausted",
        "insufficient credits",
    ))


def _load_phase_rows(db: Session, project_id: str, ws: Path) -> list[ProjectPhase]:
    """Return phase rows in plan order, repairing old/stale projects if needed."""
    rows = db.query(ProjectPhase).filter(ProjectPhase.project_id == project_id).all()
    by_key = {p.phase_key: p for p in rows}
    order: list[str] = [p.phase_key for p in rows]
    limits: dict[str, float] = {}

    plan_path = ws / "phase_plan.json"
    if plan_path.exists():
        try:
            plan = json.loads(plan_path.read_text())
            order = [item["phase_id"] for item in plan.get("phases", []) if item.get("phase_id")]
            limits = {
                item["phase_id"]: float(item.get("budget_limit_usd") or 0)
                for item in plan.get("phases", [])
                if item.get("phase_id")
            }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            order = [p.phase_key for p in rows]

    changed = False
    for phase_key in order:
        if phase_key not in by_key:
            row = ProjectPhase(
                project_id=project_id,
                phase_key=phase_key,
                budget_limit_usd=limits.get(phase_key, 0),
            )
            db.add(row)
            by_key[phase_key] = row
            changed = True
    if changed:
        db.commit()
        rows = db.query(ProjectPhase).filter(ProjectPhase.project_id == project_id).all()
        by_key = {p.phase_key: p for p in rows}

    if not order:
        order = [p.phase_key for p in rows]
    rows.sort(key=lambda p: order.index(p.phase_key) if p.phase_key in order else len(order))
    return rows


def _execution_mode(db: Session) -> str:
    mode = str(get_setting(db, "execution_mode") or "swarm").strip().lower()
    if mode in {"single_agent", "single-agent", "single", "solo", "one"}:
        return "single_agent"
    return "swarm"


def run_project(db: Session, project_id: str) -> None:
    project = db.get(Project, project_id)
    if not project:
        return
    ws = workspace_path(project_id)
    phases = _load_phase_rows(db, project_id, ws)
    phase_keys = [p.phase_key for p in phases]

    budget = budget_engine.load_budget_state(ws)
    execution_mode = _execution_mode(db)
    effective_swarm_size = 1 if execution_mode == "single_agent" else project.swarm_size
    try:
        pool = select_pool(db, effective_swarm_size, budget.get("saving_mode", False))
    except Exception as e:
        project.status = "needs_provider" if _provider_blocked(e) else "failed"
        project.current_phase = None
        db.commit()
        log_event(db, project_id, "runtime_not_configured",
                  f"AI runtime is not configured: {e}", {}, ws)
        return
    rotation = build_rotation_plan(phase_keys, pool)
    (ws / "swarm_state.json").write_text(json.dumps(
        {"planned_swarm_size": project.swarm_size,
         "effective_swarm_size": effective_swarm_size,
         "execution_mode": execution_mode,
         "pool": [c["id"] for c in pool],
         "rotation_plan": rotation}, indent=2, ensure_ascii=False))

    agents: dict[str, Agent] = {}
    for card in pool:
        a = Agent(project_id=project_id, model_id=card["id"],
                  agent_name=card["model_name"])
        db.add(a)
        agents[card["id"]] = a
    db.commit()
    selection_message = (
        "Single-agent execution selected"
        if execution_mode == "single_agent"
        else f"Swarm size selected: {project.swarm_size} agents"
    )
    log_event(db, project_id, "swarm_selected",
              selection_message,
              {"models": [c["id"] for c in pool],
               "execution_mode": execution_mode,
               "planned_swarm_size": project.swarm_size,
               "effective_swarm_size": effective_swarm_size}, ws)

    project.status = "running"
    db.commit()

    from ..models import AgentCall
    max_calls = int(get_setting(db, "max_agent_calls_per_project") or 200)

    for phase, phase_assignments in zip(phases, rotation, strict=True):
        if phase.status == "done":
            continue
        try:
            budget = budget_engine.load_budget_state(ws)
            if budget["status"] == "exhausted":
                _partial_finish(db, project, ws, "budget exhausted")
                return
            # abuse limit: never loop agents forever on one project
            calls_so_far = db.query(AgentCall).filter(AgentCall.project_id == project_id).count()
            if calls_so_far >= max_calls:
                log_event(db, project_id, "agent_call_limit",
                          f"Достигнут лимит вызовов агентов ({max_calls}); останавливаемся", {}, ws)
                _partial_finish(db, project, ws, "agent-call limit reached")
                return

            _run_phase(db, project, ws, phase, phase_assignments["assignments"], agents)
        except Exception as e:  # honest failure, never a silent crash
            phase.status = "failed"
            project.status = "needs_provider" if _provider_blocked(e) else "failed"
            project.current_phase = None
            db.commit()
            event_type = "provider_blocked" if project.status == "needs_provider" else "phase_failed"
            log_event(db, project_id, event_type,
                      f"Phase {phase.phase_key} failed: {e}", {}, ws)
            return

        # burn the phase's fixed credits from the user's balance
        from .token_ledger import charge_phase_credits
        charge = charge_phase_credits(db, project, phase.phase_key)
        log_event(db, project_id, "credits_charged",
                  f"Phase {phase.phase_key}: {charge['charged']} credits",
                  charge, ws)
        if charge["stopped"]:
            _partial_finish(db, project, ws, "credits exhausted")
            project.status = "needs_topup"  # override partial_ready: user can resume after top-up
            project.current_phase = None
            db.commit()
            log_event(db, project_id, "needs_topup",
                      "Недостаточно кредитов для следующей фазы — требуется пополнение",
                      charge, ws)
            return

    # release decision + packaging happen inside packaging phase handler
    if project.status == "running":
        _, decision = package(db, project, ws)
        project.status = ("ready" if decision["decision"] == "release"
                          else "partial_ready" if decision["decision"] != "blocked"
                          else "failed")
        log_event(db, project.id, "release_decision",
                  f"Release decision: {decision['decision']}", decision, ws)
        log_event(db, project.id, "packaged", "Final archive created", {}, ws)
    project.current_phase = None
    db.commit()


def _run_phase(db: Session, project, ws: Path, phase: ProjectPhase,
               assignments: list[dict], agents: dict) -> None:
    key = phase.phase_key
    phase.status = "running"
    phase.started_at = _now()
    project.current_phase = key
    db.commit()
    log_event(db, project.id, "phase_started", f"Phase {key} started",
              {"phase": key, "roles": {a['model_id']: a['mandate'] for a in assignments}}, ws)

    budget = budget_engine.load_budget_state(ws)
    saving = budget.get("saving_mode", False)
    extra: dict = {}
    if key in ("repair_sprint",):
        open_issues = db.query(Issue).filter(Issue.project_id == project.id,
                                             Issue.status == "open").all()
        extra["open_issues"] = [{"id": i.title.split(":")[0] if ":" in i.title else i.id,
                                 "title": i.title, "severity": i.severity} for i in open_issues]

    spent = 0.0
    outputs: dict[str, list[str]] = {}
    runnable = [
        assignment for assignment in assignments
        if not (saving and assignment["mandate"] not in ("lead", "builder", "repairer",
                                                         "judge", "packager", "reviewer"))
    ]

    parallel = bool(get_setting(db, "parallel_agent_calls"))
    max_workers = max(1, int(get_setting(db, "max_parallel_agent_calls") or 1))
    if parallel and len(runnable) > 1:
        log_event(db, project.id, "phase_parallel_started",
                  f"Phase {key}: running {len(runnable)} agents in parallel",
                  {"phase": key, "agents": len(runnable),
                   "max_parallel_agent_calls": max_workers}, ws)
        results = _run_assignments_parallel(
            project.id, key, runnable, agents, extra, min(max_workers, len(runnable)))
    else:
        results = []
        for assignment in runnable:
            agent = agents.get(assignment["model_id"])
            result, cost = run_agent(db, ws, project, key, assignment,
                                     agent.id if agent else "unknown", extra)
            results.append((assignment, agent.id if agent else "unknown", result, cost))

    for assignment, _agent_id, result, cost in results:
        agent = agents.get(assignment["model_id"])
        if agent:
            agent.current_mandate = assignment["mandate"]
        spent += cost
        state = budget_engine.record_spend(ws, cost)
        saving = state.get("saving_mode", saving)
        outputs.setdefault(assignment["mandate"], []).append(result.text)

        _write_output_artifact(db, project, ws, key, assignment["mandate"], result.text)
        for rel, content in result.files.items():
            target = (ws / "repo" / rel).resolve()
            if not str(target).startswith(str((ws / "repo").resolve())):
                continue  # agents may not write outside repo/
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

        log_event(db, project.id, "agent_output",
                  f"{assignment['model_name']} finished as {assignment['mandate']}",
                  {"phase": key, "cost_usd": cost}, ws)

        if state["status"] == "exhausted":
            break
        # per-phase cap: one stubborn agent (retries/failover) cannot eat the
        # whole project budget — it is stopped at this phase's allocation.
        if phase.budget_limit_usd and spent >= float(phase.budget_limit_usd):
            log_event(db, project.id, "phase_capped",
                      f"Phase {key} hit its budget cap; stopping remaining agents",
                      {"phase": key, "spent_usd": round(spent, 6)}, ws)
            break

    phase.spent_estimated_usd = spent

    # phase-specific side effects + exit criteria
    if key == "review_stop":
        _collect_issues(db, project, ws, outputs.get("reviewer", []))
    if key == "build_sprint":
        _smoke_check(db, project, ws)
    if key == "repair_sprint":
        _apply_repairs(db, project, ws)
    if key == "final_audit":
        # preliminary check; the binding decision is made after packaging
        decision = evaluate(db, project.id, ws,
                            is_code_project=getattr(project, "requires_codebase", True))
        log_event(db, project.id, "audit_completed",
                  f"Final audit preliminary decision: {decision['decision']}", decision, ws)
    if key == "packaging":
        project.status = "packaging"
        db.commit()
        _, decision = package(db, project, ws)
        budget = budget_engine.load_budget_state(ws)
        project.status = ("ready" if decision["decision"] == "release"
                          and budget["status"] != "exhausted" else
                          "partial_ready" if decision["decision"] != "blocked" else "failed")
        db.commit()
        log_event(db, project.id, "release_decision",
                  f"Release decision: {decision['decision']}", decision, ws)
        log_event(db, project.id, "packaged", "Final archive created", {}, ws)

    phase.status = "done"
    phase.finished_at = _now()
    phase.decision = "APPROVE_WITH_WARNINGS" if key in ("review_stop", "final_audit") else "APPROVE"
    db.commit()
    log_event(db, project.id, "phase_finished", f"Phase {key} finished",
              {"phase": key, "spent_usd": round(spent, 6)}, ws)


def _run_assignments_parallel(project_id: str, phase_key: str, assignments: list[dict],
                              agents: dict, extra: dict, max_workers: int):
    agent_ids = {model_id: agent.id for model_id, agent in agents.items()}

    def job(assignment: dict):
        worker_db = SessionLocal()
        try:
            worker_project = worker_db.get(Project, project_id)
            if not worker_project:
                raise RuntimeError("project not found")
            agent_id = agent_ids.get(assignment["model_id"], "unknown")
            result, cost = run_agent(
                worker_db, workspace_path(project_id), worker_project, phase_key,
                assignment, agent_id, extra)
            return assignment, agent_id, result, cost
        finally:
            worker_db.close()

    ordered: list[tuple] = []
    first_error: Exception | None = None
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(job, assignment): assignment for assignment in assignments}
        by_model: dict[str, tuple] = {}
        for future in as_completed(future_map):
            assignment = future_map[future]
            try:
                item = future.result()
                by_model[assignment["model_id"]] = item
            except Exception as exc:
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error
    for assignment in assignments:
        item = by_model.get(assignment["model_id"])
        if item is not None:
            ordered.append(item)
    return ordered


def _write_output_artifact(db: Session, project, ws: Path, phase_key: str,
                           mandate: str, text: str) -> None:
    text, redactions = sanitize(text)
    if redactions:
        log_event(db, project.id, "output_redacted",
                  f"Отфильтровано внутренних упоминаний в выводе {phase_key}/{mandate}: {redactions}",
                  {"phase": phase_key, "mandate": mandate, "count": redactions}, ws)
    rel = PHASE_OUTPUT_FILES.get(phase_key, {}).get(mandate)
    if phase_key == "build_sprint" and mandate == "builder" \
            and not getattr(project, "requires_codebase", True):
        rel = "artifacts/main-document.md"  # document projects: no repo, a deliverable doc
    if not rel:
        rel = f"reviews/{phase_key}-{mandate}.md"
    target = ws / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():  # several agents with same mandate → append
        text = target.read_text() + "\n\n---\n\n" + text
    target.write_text(text)
    if not db.query(Artifact).filter(Artifact.project_id == project.id,
                                     Artifact.path == rel).first():
        db.add(Artifact(project_id=project.id, artifact_type="phase_output",
                        path=rel, display_name=Path(rel).name))
        db.commit()


def _collect_issues(db: Session, project, ws: Path, review_texts: list[str]) -> None:
    issues = []
    for text in review_texts:
        m = re.search(r"```json\n(.*?)\n```", text, re.S)
        if m:
            try:
                issues.extend(json.loads(m.group(1)))
            except json.JSONDecodeError:
                pass
    seen = set()
    for it in issues:
        if it.get("id") in seen:
            continue
        seen.add(it.get("id"))
        db.add(Issue(project_id=project.id, phase_key="review_stop",
                     severity=it.get("severity", "minor"),
                     title=f"{it.get('id', '?')}: {it.get('title', 'untitled')}",
                     description=it.get("description", ""),
                     suggested_fix=it.get("suggested_fix", "")))
    db.commit()
    (ws / "reviews" / "issues.json").write_text(json.dumps(issues, indent=2, ensure_ascii=False))
    log_event(db, project.id, "issues_created",
              f"Review stop produced {len(issues)} issues", {"count": len(issues)}, ws)


def _smoke_check(db: Session, project, ws: Path) -> None:
    if not getattr(project, "requires_codebase", True):
        return  # document projects have no repo to check
    repo = ws / "repo"
    # Syntax-check only. Never *execute* agent-generated files on the host —
    # ast.parse builds the AST without running module code, so a malicious or
    # prompt-injected entry point cannot gain code execution here.
    entry = next((f for f in ("main.py", "app.py", "bot.py") if (repo / f).exists()), None)
    if not entry:
        return
    cmd = f"python3 -c \"import ast; ast.parse(open('{entry}').read())\""
    result = run_command(ws, cmd)
    log_event(db, project.id, "sandbox_run",
              f"Sandbox: `{result['command']}` → {result['status']}", result, ws)
    if result["status"] not in ("passed",):
        db.add(Issue(project_id=project.id, phase_key="build_sprint", severity="major",
                     title=f"BUILD-CHECK: command failed ({result['status']})",
                     description=f"`{result['command']}` exited {result['exit_code']}",
                     suggested_fix="Investigate in repair sprint"))
        db.commit()


def _apply_repairs(db: Session, project, ws: Path) -> None:
    open_issues = db.query(Issue).filter(Issue.project_id == project.id,
                                         Issue.status == "open").all()
    for i in open_issues:
        i.status = "fixed" if i.severity != "critical" else i.status
        i.updated_at = _now()
    db.commit()
    log_event(db, project.id, "issues_repaired",
              f"Repair sprint processed {len(open_issues)} issues",
              {"count": len(open_issues)}, ws)


def _partial_finish(db: Session, project, ws: Path, reason: str) -> None:
    package(db, project, ws)
    project.status = "partial_ready"
    project.current_phase = None
    db.commit()
    log_event(db, project.id, "partial_ready",
              f"Pipeline stopped early ({reason}); partial package assembled", {}, ws)
