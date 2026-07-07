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
from . import budget_engine, build_integrity
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
    """Transient/exhaustion faults — the runtime is configured but momentarily
    unavailable (rate limits, quota, overload). Recoverable → needs_provider."""
    text = str(exc).lower()
    return any(marker in text for marker in (
        "all usable keys failed",
        "too many requests",
        "rate limit",
        "rate_limit",
        "quota",
        "resourceexhausted",
        "overloaded",
        "insufficient credits",
    ))


def _provider_config_error(exc: Exception | str) -> bool:
    """Setup faults — no runtime is wired up at all. The operator must act; a
    client never sees this as a delivered result → provider_config_error."""
    text = str(exc).lower()
    return any(marker in text for marker in (
        "no usable real api keys",
        "no usable api keys",
        "no api key configured",
        "no enabled real model",
        "no usable real api keys are available",
        "no enabled real model with usable api keys",
    ))


def _provider_status(exc: Exception | str) -> str:
    """Honest terminal status for a provider-side failure."""
    if _provider_config_error(exc):
        return "provider_config_error"
    if _provider_blocked(exc):
        return "needs_provider"
    return "failed"


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
    # a project can pin its own mode ("fast"/single_agent); otherwise the global
    # setting applies. Per-project choice wins so a fast one-button build stays
    # fast even when the platform default is the full swarm.
    project_mode = str(getattr(project, "execution_mode", "") or "").strip().lower()
    if project_mode in ("single_agent", "single-agent", "single", "solo", "one", "fast"):
        execution_mode = "single_agent"
    elif project_mode == "swarm":
        execution_mode = "swarm"
    else:
        execution_mode = _execution_mode(db)
    effective_swarm_size = 1 if execution_mode == "single_agent" else project.swarm_size
    try:
        pool = select_pool(db, effective_swarm_size, budget.get("saving_mode", False))
    except Exception as e:
        project.status = _provider_status(e)
        project.current_phase = None
        project.not_released_reason = f"AI runtime unavailable: {e}"
        db.commit()
        event_type = ("provider_config_error" if project.status == "provider_config_error"
                      else "runtime_not_configured")
        log_event(db, project_id, event_type,
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
            project.status = _provider_status(e)
            project.current_phase = None
            project.not_released_reason = f"phase {phase.phase_key} failed: {e}"
            db.commit()
            event_type = ("provider_config_error" if project.status == "provider_config_error"
                          else "provider_blocked" if project.status == "needs_provider"
                          else "phase_failed")
            log_event(db, project_id, event_type,
                      f"Phase {phase.phase_key} failed: {e}", {}, ws)
            return

        # Honest progress accounting (spec §7.7): a phase only earns money when it
        # left evidence behind. A build phase that parsed no files, or any phase
        # that produced nothing, is an internal failure — the client is not
        # charged and the project cannot be presented as a finished result.
        if not phase.made_progress:
            reason = (phase.progress_proof or {}).get("reason", "no progress")
            log_event(db, project_id, "phase_no_progress",
                      f"Phase {phase.phase_key} made no chargeable progress: {reason}",
                      phase.progress_proof or {}, ws)
            if float(phase.spent_estimated_usd or 0) > 0:
                # explicit platform-failure accounting: the API burned money,
                # the client is not billed, and the loss is visible to the founder.
                log_event(db, project_id, "platform_failure",
                          f"Провайдер потратил ${float(phase.spent_estimated_usd):.4f} "
                          f"на фазу {phase.phase_key} без результата — этап не оплачивается клиентом",
                          {"phase": phase.phase_key,
                           "spent_usd": float(phase.spent_estimated_usd),
                           "reason": reason}, ws)
            if phase.phase_key in ("build_sprint", "spec_war", "architecture_battle"):
                _stop_needs_repair(db, project, ws, phase.phase_key, reason)
                return
            # Non-critical phase with no output: skip the charge, keep going.
            continue

        # burn the phase's fixed credits from the user's balance — only now that
        # progress is proven.
        from .token_ledger import charge_phase_credits
        charge = charge_phase_credits(db, project, phase.phase_key)
        phase.credits_charged = int(charge.get("charged", 0))
        db.commit()
        log_event(db, project_id, "credits_charged",
                  f"Phase {phase.phase_key}: {charge['charged']} credits (progress proven)",
                  {**charge, "progress_proof": phase.progress_proof}, ws)
        if charge["stopped"]:
            # resumable: the client tops up and continues the SAME paid project,
            # so keep the credits already spent (no refund).
            _partial_finish(db, project, ws, "credits exhausted", refund=False)
            project.status = "needs_topup"  # override partial_ready: user can resume after top-up
            project.current_phase = None
            db.commit()
            log_event(db, project_id, "needs_topup",
                      "Недостаточно кредитов для следующей фазы — требуется пополнение",
                      charge, ws)
            return

        # The final client-facing status is applied only AFTER this phase's
        # charge is recorded: a client polling the project must never observe
        # "ready" with the last phase's credits still unaccounted.
        if phase.phase_key == "packaging":
            _finalize_release(db, project, ws, _load_release_decision(db, project, ws))

    # release decision + packaging happen inside the packaging phase; this
    # fallback covers pipelines without a packaging phase (or a packaging phase
    # that produced no chargeable output and was skipped above).
    if project.status in ("running", "packaging"):
        _, decision = package(db, project, ws)
        _finalize_release(db, project, ws, decision)
    project.current_phase = None
    db.commit()


def _load_release_decision(db: Session, project, ws: Path) -> dict:
    """The decision the packaging phase persisted; recomputed only if missing."""
    path = ws / "reviews" / "release-decision.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            pass
    _, decision = package(db, project, ws)
    return decision


def _finalize_release(db: Session, project, ws: Path, decision: dict) -> None:
    """Apply the binding release decision to the project. status == 'ready'
    (and release_decision == 'release') is the ONLY combination a paying client
    may download — everything else is admin-only."""
    budget = budget_engine.load_budget_state(ws)
    verdict = decision["decision"]
    project.release_decision = verdict
    if verdict == "release" and budget["status"] != "exhausted":
        project.status = "ready"
        project.not_released_reason = ""
    elif verdict == "blocked":
        project.status = "failed"
        project.not_released_reason = ("release blocked: "
                                       + "; ".join(decision.get("notes", [])[:6]))
    else:
        project.status = "partial_ready"
        reasons = decision.get("notes", [])
        if budget["status"] == "exhausted":
            reasons = ["budget exhausted before completion", *reasons]
        project.not_released_reason = ("not released to client: "
                                       + "; ".join(reasons[:6] or ["incomplete result"]))
    db.commit()
    # Fairness: the client can only download a `ready`/`release` result. If the
    # project terminates undownloadable (blocked or partial), refund the credits
    # they were charged per phase — they must not pay for what they cannot get.
    if project.status in ("failed", "partial_ready"):
        from .token_ledger import refund_project_credits
        refund = refund_project_credits(db, project, f"not delivered: {verdict}")
        if refund.get("refunded"):
            log_event(db, project.id, "credits_refunded",
                      f"Возврат {refund['refunded']} credits: результат не доставлен клиенту ({verdict})",
                      refund, ws)
    log_event(db, project.id, "release_decision",
              f"Release decision: {verdict}", decision, ws)
    log_event(db, project.id, "packaged", "Final archive created", {}, ws)


def _stop_needs_repair(db: Session, project, ws: Path, phase_key: str, reason: str) -> None:
    """A critical phase produced no usable output. Assemble whatever exists for
    the founder to inspect, mark the project as needing internal repair, and make
    it clear the client is not charged and gets nothing final."""
    package(db, project, ws)
    project.status = "needs_internal_repair"
    project.release_decision = "needs_internal_repair"
    project.current_phase = None
    project.not_released_reason = f"internal repair needed after {phase_key}: {reason}"
    db.commit()
    # earlier phases may already have been charged for proven progress; the
    # client gets nothing final here, so make them whole.
    from .token_ledger import refund_project_credits
    refund = refund_project_credits(db, project, f"internal repair after {phase_key}")
    if refund.get("refunded"):
        log_event(db, project.id, "credits_refunded",
                  f"Возврат {refund['refunded']} credits: {phase_key} без результата",
                  refund, ws)
    log_event(db, project.id, "needs_internal_repair",
              f"Pipeline stopped: {phase_key} produced no usable output ({reason})",
              {"phase": phase_key, "reason": reason}, ws)


def _read_excerpt(path: Path, limit: int = 2000) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(errors="replace")[:limit]
    except OSError:
        return ""


def _command_log_tail(ws: Path, limit: int = 3) -> str:
    log = ws / "logs" / "command-runs.jsonl"
    if not log.exists():
        return ""
    try:
        lines = [ln for ln in log.read_text(errors="replace").splitlines() if ln.strip()]
    except OSError:
        return ""
    return "\n".join(lines[-limit:])


def _gate_failure_details(gate_result: dict) -> list[dict]:
    return [{"name": name, "detail": gate_result["gates"].get(name, {}).get("detail", "")}
            for name in gate_result.get("failed", [])]


def _apply_result_files(ws: Path, result) -> int:
    """Write an agent result's contract files into repo/ (path-confined).
    Returns how many files were applied."""
    applied = 0
    for rel, content in result.files.items():
        target = (ws / "repo" / rel).resolve()
        if not str(target).startswith(str((ws / "repo").resolve())):
            continue  # agents may not write outside repo/
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        applied += 1
    return applied


def _run_phase(db: Session, project, ws: Path, phase: ProjectPhase,
               assignments: list[dict], agents: dict) -> None:
    key = phase.phase_key
    phase.status = "running"
    phase.started_at = _now()
    project.current_phase = key
    # honest client-facing state: repair work shows as "repairing", not a
    # generic "running" that hides how long fixing takes.
    project.status = "repairing" if key == "repair_sprint" else "running"
    db.commit()
    log_event(db, project.id, "phase_started", f"Phase {key} started",
              {"phase": key, "roles": {a['model_id']: a['mandate'] for a in assignments}}, ws)

    budget = budget_engine.load_budget_state(ws)
    saving = budget.get("saving_mode", False)
    is_code_project = getattr(project, "requires_codebase", True)

    # progress accounting: snapshot the repo + open-issue count before the phase.
    repo_before = build_integrity.snapshot_repo(ws)
    issues_before = db.query(Issue).filter(Issue.project_id == project.id,
                                           Issue.status == "open").count()

    from . import integration

    extra: dict = {}
    if key == "build_sprint" and is_code_project:
        # every builder sees the same integration contract: what exists, the
        # file budget, junk-name bans, one-function-one-place
        extra["repo_files"] = _repo_listing(ws)
        extra["file_rules"] = integration.file_rules_text(db, extra["repo_files"])
    if key == "repair_sprint":
        open_issues = db.query(Issue).filter(Issue.project_id == project.id,
                                             Issue.status == "open").all()
        extra["open_issues"] = [{"id": i.title.split(":")[0] if ":" in i.title else i.id,
                                 "title": i.title, "severity": i.severity,
                                 "description": i.description or "",
                                 "suggested_fix": i.suggested_fix or ""}
                                for i in open_issues]
        gate_preview = build_integrity.run_gates(ws, is_code_project)
        extra["gate_failures"] = _gate_failure_details(gate_preview)
        extra["repo_files"] = _repo_listing(ws)
        extra["spec_excerpt"] = _read_excerpt(ws / "spec" / "technical-spec.md")
    if key in ("review_stop", "final_audit"):
        # Review/audit must see the real repo + spec + failed checks + recent
        # build logs, not just prior prose, so a rubber-stamp on an empty or
        # broken build is impossible.
        extra["repo_files"] = _repo_listing(ws)
        gate_preview = build_integrity.run_gates(ws, is_code_project)
        extra["build_gate_summary"] = {
            "passed": gate_preview["passed"],
            "failed": gate_preview["failed"],
        }
        extra["gate_failures"] = _gate_failure_details(gate_preview)
        extra["spec_excerpt"] = _read_excerpt(ws / "spec" / "technical-spec.md")
        extra["build_log_tail"] = _command_log_tail(ws)

    spent = 0.0
    parsed_files = 0  # files emitted through the builder/repairer file contract
    mock_fallback_files = 0
    outputs: dict[str, list[str]] = {}
    runnable = [
        assignment for assignment in assignments
        if not (saving and assignment["mandate"] not in ("lead", "builder", "repairer",
                                                         "judge", "packager", "reviewer"))
    ]

    results = None
    if key == "build_sprint" and is_code_project:
        from . import micro_build
        if micro_build.should_microtask(db, runnable):
            worker = next((a for a in runnable if a["mandate"] == "builder"), runnable[0])
            agent = agents.get(worker["model_id"])
            log_event(db, project.id, "micro_build_started",
                      "Единственная доступная модель — сборка разбита на микрозадачи",
                      {"phase": key, "model": worker.get("model_name", "")}, ws)
            results = micro_build.run_micro_build(
                db, ws, project, key, worker, agent.id if agent else "unknown",
                float(phase.budget_limit_usd or 0), base_extra=extra)
            # None → the model returned no usable plan; fall back to one shot.
        elif len(runnable) > 1 and bool(get_setting(db, "enable_integration_plan")):
            # COORDINATOR step: one binding file plan before any builder runs,
            # so parallel agents never produce alternative implementations of
            # the same thing.
            plan_cost = _coordinate_build_plan(db, project, ws, key, runnable,
                                               agents, extra)
            if plan_cost:
                spent += plan_cost
                budget_engine.record_spend(ws, plan_cost)

    if results is None:
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

    manifests: list[dict] = []
    for assignment, _agent_id, result, cost in results:
        agent = agents.get(assignment["model_id"])
        if agent:
            agent.current_mandate = assignment["mandate"]
        spent += cost
        state = budget_engine.record_spend(ws, cost)
        saving = state.get("saving_mode", saving)
        outputs.setdefault(assignment["mandate"], []).append(result.text)

        # structured agent contract: material for the integrator, not the user
        manifest = integration.parse_agent_manifest(result.text)
        if manifest:
            manifests.append({"mandate": assignment["mandate"],
                              "slot": assignment.get("agent_slot"), **manifest})

        _write_output_artifact(db, project, ws, key, assignment["mandate"], result.text)
        applied = _apply_result_files(ws, result)
        if getattr(result, "status", "") == "mock_fallback":
            # a mock stood in for a failed real model: keep the draft on disk
            # for the founder, but it is NOT billable progress by the model.
            mock_fallback_files += applied
            log_event(db, project.id, "mock_fallback_used",
                      f"{assignment['model_name']} ({assignment['mandate']}) заменён mock — "
                      "результат не засчитывается как прогресс",
                      {"phase": key, "mandate": assignment["mandate"],
                       "files": applied}, ws)
        else:
            parsed_files += applied  # honest "built something" signal (spec §7.7)

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

    # Models regularly bury code inside prose documents instead of the FILE
    # contract. Salvage it into repo/ so the work is judged (and billed) by
    # what actually exists, not by where the model happened to put it.
    if key == "build_sprint" and is_code_project:
        salvaged = build_integrity.salvage_files_from_documents(ws)
        if salvaged:
            parsed_files += len(salvaged)
            log_event(db, project.id, "files_salvaged",
                      f"Извлечено {len(salvaged)} файл(ов) кода из документов в repo/",
                      {"files": salvaged}, ws)

    # INTEGRATION PASS — mandatory after any phase that writes code: junk and
    # exact duplicates are removed deterministically; anything needing judgment
    # goes to the LLM integrator so the user always receives ONE coherent tree.
    if key in ("build_sprint", "repair_sprint") and is_code_project:
        integration_report = integration.integration_pass(db, ws)
        if integration_report["removed"] or integration_report["needs_review"]:
            log_event(db, project.id, "integration_pass",
                      f"Интеграция: удалено {len(integration_report['removed'])} "
                      f"файл(ов), на разбор {len(integration_report['needs_review'])}",
                      integration_report, ws)
        if (key == "build_sprint" and integration_report["needs_review"]
                and bool(get_setting(db, "enable_llm_integrator"))):
            spent += _run_integrator(db, project, ws, key, runnable, agents,
                                     integration_report, manifests, phase)
        phase.spent_estimated_usd = spent  # integrator spend counts too

    # phase-specific side effects + exit criteria
    if key == "review_stop":
        _collect_issues(db, project, ws, outputs.get("reviewer", []))
    if key == "build_sprint":
        _smoke_check(db, project, ws)
    if key == "final_audit":
        # Reviews describe the repo as it was; the repo has moved since (salvage,
        # repairs). Close issues that claim files are missing when those files
        # now exist, so the verdict is judged against the CURRENT tree.
        _revalidate_open_issues(db, project, ws)
        # deterministic gates run here so failed checks become tracked issues
        # (spec §7.9) — and hard failures get a real, verified repair loop
        # before the audit verdict is recorded.
        gate_result = build_integrity.run_gates(ws, is_code_project)
        created = build_integrity.issues_from_gate_failures(db, project.id, gate_result)
        if created:
            log_event(db, project.id, "issues_created",
                      f"Deterministic gates opened {created} issue(s)",
                      {"gate_failures": gate_result["failed"]}, ws)
        gate_result, repair_spent = _gate_repair_loop(
            db, project, ws, phase, assignments, agents, gate_result, is_code_project)
        spent += repair_spent
        phase.spent_estimated_usd = spent
        decision = evaluate(db, project.id, ws, is_code_project=is_code_project)
        log_event(db, project.id, "audit_completed",
                  f"Final audit preliminary decision: {decision['decision']}", decision, ws)

    # honest progress proof for this phase, computed from on-disk evidence
    # (after salvage/gate repairs, so verified fixes count and fakes do not).
    repo_after = build_integrity.snapshot_repo(ws)
    repo_diff = build_integrity.diff_repo(repo_before, repo_after)
    repo_changed = parsed_files > 0 or repo_diff.get("files_written", 0) > 0 \
        or repo_diff.get("files_changed", 0) > 0

    if key == "repair_sprint":
        _apply_repairs(db, project, ws, repo_changed=repo_changed,
                       is_code_project=is_code_project)

    issues_after = db.query(Issue).filter(Issue.project_id == project.id,
                                          Issue.status == "open").count()
    progress = build_integrity.assess_phase_progress(
        ws, key, repo_diff=repo_diff, outputs=outputs,
        issues_before=issues_before, issues_after=issues_after,
        is_code_project=is_code_project, parsed_files=parsed_files)
    progress["signals"]["mock_fallback_files"] = mock_fallback_files
    if results and all(getattr(r, "status", "") == "mock_fallback"
                       for _, _, r, _ in results):
        # every real model failed and a mock stood in for all of them: that is
        # a provider failure to escalate, never billable client progress.
        progress["made_progress"] = False
        progress["reason"] = "all outputs came from mock fallback (provider failure)"
    phase.made_progress = progress["made_progress"]
    phase.progress_proof = progress

    if key == "packaging":
        # Package + auto-recover here, but DO NOT apply the final client-facing
        # status yet: billing for this phase happens in run_project after the
        # progress proof, and a project must never read "ready" before its last
        # charge is recorded (the client would see ready with a stale credit
        # total). run_project finalizes from reviews/release-decision.json.
        project.status = "packaging"
        db.commit()
        _, decision = package(db, project, ws)
        if decision["decision"] != "release":
            decision, recovery_spent = _attempt_release_recovery(
                db, project, ws, phase, assignments, agents, is_code_project, decision)
            spent += recovery_spent
            phase.spent_estimated_usd = spent

    phase.status = "done"
    phase.finished_at = _now()
    phase.decision = "APPROVE_WITH_WARNINGS" if key in ("review_stop", "final_audit") else "APPROVE"
    if project.status == "repairing":
        project.status = "running"
    db.commit()
    log_event(db, project.id, "phase_finished", f"Phase {key} finished",
              {"phase": key, "spent_usd": round(spent, 6),
               "made_progress": phase.made_progress,
               "progress": progress["reason"]}, ws)


def _coordinate_build_plan(db: Session, project, ws: Path, phase_key: str,
                           runnable: list[dict], agents: dict, extra: dict) -> float:
    """COORDINATOR step: one model produces the binding file plan (paths,
    purposes, owners, forbidden files) that every builder must follow. On any
    failure the build proceeds without a plan — the integration pass still
    cleans up afterwards."""
    from . import integration
    coordinator = next((a for a in runnable if a["mandate"] == "lead"), runnable[0])
    agent = agents.get(coordinator["model_id"])
    try:
        result, cost = run_agent(
            db, ws, project, phase_key,
            {**coordinator, "mandate": "lead"},
            agent.id if agent else "unknown",
            {"repo_files": extra.get("repo_files", []),
             "micro_task": integration.plan_task_text(db, extra.get("repo_files", []))})
    except Exception as exc:
        log_event(db, project.id, "integration_plan_failed",
                  f"Координатор не смог составить план интеграции: {exc}",
                  {"phase": phase_key}, ws)
        return 0.0
    result.files = {}  # the plan is coordination, never repo content
    plan = integration.parse_integration_plan(result.text)
    if plan is None or getattr(result, "status", "") == "mock_fallback":
        log_event(db, project.id, "integration_plan_failed",
                  "Координатор не вернул валидный план — сборка без плана",
                  {"phase": phase_key}, ws)
        return cost
    (ws / "integration_plan.json").write_text(
        json.dumps(plan, indent=2, ensure_ascii=False))
    extra["integration_plan"] = integration.plan_context_text(plan)
    log_event(db, project.id, "integration_plan_created",
              f"План интеграции: {len(plan['files'])} файлов, один владелец на файл",
              {"files": [f["path"] for f in plan["files"]]}, ws)
    return cost


def _run_integrator(db: Session, project, ws: Path, phase_key: str,
                    runnable: list[dict], agents: dict, report: dict,
                    manifests: list[dict], phase: ProjectPhase) -> float:
    """FINAL INTEGRATOR call: resolve what the deterministic pass could not —
    near-duplicates, parallel implementations, budget overruns. Applies merged
    files and explicit `DELETE:` verdicts, then re-runs the deterministic pass."""
    from ..lib.file_extractor import extract_deletions
    from . import integration
    from .access_control import ACCESS_BY_MANDATE

    state = budget_engine.load_budget_state(ws)
    if state["status"] == "exhausted":
        return 0.0
    base = next((a for a in runnable if a["mandate"] in ("judge", "lead")), runnable[-1])
    assignment = {**base, "mandate": "integrator",
                  "access": ACCESS_BY_MANDATE.get("integrator", [])}
    agent = agents.get(base["model_id"])
    try:
        result, cost = run_agent(
            db, ws, project, phase_key, assignment,
            agent.id if agent else "unknown",
            {"repo_files": _repo_listing(ws),
             "micro_task": integration.integrator_task_text(report, manifests)})
    except Exception as exc:
        log_event(db, project.id, "integrator_failed",
                  f"Интегратор не выполнился: {exc}", {"phase": phase_key}, ws)
        return 0.0
    budget_engine.record_spend(ws, cost)
    if getattr(result, "status", "") == "mock_fallback":
        return cost  # a mock cannot merge a real build
    applied = _apply_result_files(ws, result)
    deleted = integration.apply_deletions(ws, extract_deletions(result.text))
    final_report = integration.integration_pass(db, ws)
    log_event(db, project.id, "integrator_finished",
              f"Интегратор: {applied} файл(ов) объединено, {len(deleted)} удалено",
              {"applied": applied, "deleted": deleted,
               "still_needs_review": final_report["needs_review"],
               "cost_usd": cost}, ws)
    return cost


def _gate_repair_loop(db: Session, project, ws: Path, phase: ProjectPhase,
                      assignments: list[dict], agents: dict, gate_result: dict,
                      is_code_project: bool) -> tuple[dict, float]:
    """Run repair agents against concrete gate failures until the hard gates
    pass or the loop/budget limits are hit. Every iteration re-runs the gates:
    an issue only closes when the machine check that opened it passes again."""
    from ..models import AgentCall
    from .access_control import ACCESS_BY_MANDATE

    max_loops = max(0, int(get_setting(db, "max_repair_loops") or 3))
    max_calls = int(get_setting(db, "max_agent_calls_per_project") or 200)
    spent = 0.0
    loop_no = 0

    while gate_result["hard_failed"] and loop_no < max_loops:
        state = budget_engine.load_budget_state(ws)
        if state["status"] == "exhausted":
            break
        if db.query(AgentCall).filter(AgentCall.project_id == project.id).count() >= max_calls:
            break
        loop_no += 1
        project.status = "repairing"
        db.commit()

        base = assignments[0]
        repair_assignment = {**base, "mandate": "repairer",
                             "access": ACCESS_BY_MANDATE.get("repairer", [])}
        agent = agents.get(base["model_id"])
        log_event(db, project.id, "gate_repair_started",
                  f"Repair attempt {loop_no}/{max_loops}: {', '.join(gate_result['hard_failed'])}",
                  {"attempt": loop_no, "hard_failed": gate_result["hard_failed"]}, ws)
        try:
            result, cost = run_agent(
                db, ws, project, phase.phase_key, repair_assignment,
                agent.id if agent else "unknown",
                {"gate_failures": _gate_failure_details(gate_result),
                 "repo_files": _repo_listing(ws),
                 "spec_excerpt": _read_excerpt(ws / "spec" / "technical-spec.md"),
                 "micro_task": "Fix ONLY the failed checks above. Re-emit each "
                               "changed file completely via the FILE contract."})
        except Exception as exc:
            log_event(db, project.id, "gate_repair_failed",
                      f"Repair attempt {loop_no} failed: {exc}", {"attempt": loop_no}, ws)
            break
        spent += cost
        budget_engine.record_spend(ws, cost)
        if getattr(result, "status", "") == "mock_fallback":
            break  # a mock cannot honestly repair a real build
        _apply_result_files(ws, result)

        gate_result = build_integrity.run_gates(ws, is_code_project)
        _close_verified_gate_issues(db, project.id, gate_result)
        log_event(db, project.id, "gate_repair_finished",
                  f"Repair attempt {loop_no}: hard failures now "
                  f"{gate_result['hard_failed'] or 'none'}",
                  {"attempt": loop_no, "failed": gate_result["failed"],
                   "cost_usd": cost}, ws)

    if project.status == "repairing":
        project.status = "running"
        db.commit()
    return gate_result, spent


_MISSING_CLAIM = re.compile(
    r"(?i)\b(missing|absent|not\s+found|does\s+not\s+exist|отсутству|не\s+найден|нет\s+файла)\b")
_PATH_TOKEN = re.compile(r"[\w/\-]+\.[A-Za-z0-9]{1,10}")


def _revalidate_open_issues(db: Session, project, ws: Path) -> int:
    """Close review issues that have gone stale: an issue complaining that
    files are missing, when every file it names now exists in the repo, is a
    description of an older snapshot — not a defect of the current one."""
    repo = ws / "repo"
    closed = 0
    open_issues = db.query(Issue).filter(Issue.project_id == project.id,
                                         Issue.status == "open").all()
    for issue in open_issues:
        if issue.title.startswith("GATE-"):
            continue  # gate issues are closed only by their gate re-passing
        text = f"{issue.title}\n{issue.description or ''}"
        if not _MISSING_CLAIM.search(text):
            continue
        paths = [p for p in _PATH_TOKEN.findall(text)
                 if "." in p and not p.endswith((".md.", ".py."))]
        if not paths:
            continue
        if all((repo / p).exists() or (repo / Path(p).name).exists() for p in paths):
            issue.status = "fixed"
            issue.updated_at = _now()
            closed += 1
    if closed:
        db.commit()
        log_event(db, project.id, "issues_stale_closed",
                  f"Закрыто {closed} устаревших замечаний: указанные файлы уже существуют",
                  {"closed": closed}, ws)
    return closed


def _attempt_release_recovery(db: Session, project, ws: Path, phase: ProjectPhase,
                              assignments: list[dict], agents: dict,
                              is_code_project: bool, decision: dict) -> tuple[dict, float]:
    """Packaging produced a non-release verdict: try to reach `release` without
    any human in the loop — drop stale issues, run the verified gate-repair
    loop against the FINAL tree, then re-package. Bounded by max_repair_loops
    and the budget; an honest partial stays partial if recovery fails."""
    from . import integration
    log_event(db, project.id, "release_recovery_started",
              f"Автовосстановление релиза: {decision['decision']}",
              {"notes": decision.get("notes", [])[:6]}, ws)
    spent = 0.0
    _revalidate_open_issues(db, project, ws)
    if is_code_project:
        integration.integration_pass(db, ws)  # junk/dupes must not block release
    gate_result = build_integrity.run_gates(ws, is_code_project)
    if gate_result["hard_failed"]:
        gate_result, spent = _gate_repair_loop(
            db, project, ws, phase, assignments, agents, gate_result, is_code_project)
    _close_verified_gate_issues(db, project.id, gate_result)
    # re-package: redaction, sanitization and the release decision all rerun
    # over the repaired final tree
    _, new_decision = package(db, project, ws)
    log_event(db, project.id, "release_recovery_finished",
              f"Автовосстановление: {decision['decision']} → {new_decision['decision']}",
              {"before": decision["decision"], "after": new_decision["decision"],
               "spent_usd": round(spent, 6)}, ws)
    return new_decision, spent


def _close_verified_gate_issues(db: Session, project_id: str, gate_result: dict) -> int:
    """Close GATE-* issues whose deterministic check passes again — the only
    evidence that counts as 'fixed'."""
    passing = {name for name, g in gate_result["gates"].items() if g["passed"]}
    closed = 0
    open_gate_issues = (db.query(Issue)
                        .filter(Issue.project_id == project_id, Issue.status == "open")
                        .all())
    for issue in open_gate_issues:
        if not issue.title.startswith("GATE-"):
            continue
        if issue.title.removeprefix("GATE-") in passing:
            issue.status = "fixed"
            issue.updated_at = _now()
            closed += 1
    if closed:
        db.commit()
    return closed


def _repo_listing(ws: Path) -> list[str]:
    repo = ws / "repo"
    if not repo.exists():
        return []
    return sorted(str(f.relative_to(repo)) for f in repo.rglob("*") if f.is_file())[:80]


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
    from . import integration
    text = integration.strip_manifest(text)  # internal contract, never user-facing
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


def _review_severity(raw: str | None) -> str:
    """Severity for an agent-reported review issue, capped at `major`.

    Only deterministic build gates (GATE-* issues from build_integrity) may be
    `critical`, because `critical` is the one severity that hard-blocks the
    client download (see release_policy.evaluate). Review agents self-assign
    severity and routinely over-escalate or hallucinate blockers that contradict
    the passing gates — e.g. "missing requirements.txt" on a valid stdlib-only
    project. Such an agent `critical` can never auto-close (no gate backs it),
    so it would sink an otherwise shippable, gate-verified build forever. We keep
    the finding visible and repair-eligible as `major`, but the block/no-block
    authority stays with the objective gates.
    """
    value = (raw or "minor").strip().lower()
    if value in ("critical", "blocker", "high", "major"):
        return "major"
    if value == "minor":
        return "minor"
    return "minor"


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
                     severity=_review_severity(it.get("severity")),
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


def _apply_repairs(db: Session, project, ws: Path, *, repo_changed: bool,
                   is_code_project: bool) -> None:
    """Close issues only on evidence, never on the repairer's say-so:

    * a GATE-* issue closes when its deterministic check passes again;
    * other non-critical issues close only when the repair sprint actually
      changed the repo (a repairer that touched nothing fixed nothing);
    * critical issues never auto-close without a passing gate.
    """
    gate_result = build_integrity.run_gates(ws, is_code_project)
    passing = {name for name, g in gate_result["gates"].items() if g["passed"]}
    open_issues = db.query(Issue).filter(Issue.project_id == project.id,
                                         Issue.status == "open").all()
    closed = 0
    for i in open_issues:
        if i.title.startswith("GATE-"):
            if i.title.removeprefix("GATE-") in passing:
                i.status = "fixed"
                i.updated_at = _now()
                closed += 1
        elif repo_changed and i.severity != "critical":
            i.status = "fixed"
            i.updated_at = _now()
            closed += 1
    db.commit()
    log_event(db, project.id, "issues_repaired",
              f"Repair sprint verified {closed} of {len(open_issues)} open issue(s) fixed",
              {"closed": closed, "open_before": len(open_issues),
               "repo_changed": repo_changed}, ws)


def _partial_finish(db: Session, project, ws: Path, reason: str,
                    refund: bool = True) -> None:
    package(db, project, ws)
    project.status = "partial_ready"
    project.release_decision = "partial_release"
    project.current_phase = None
    project.not_released_reason = f"stopped early: {reason}"
    db.commit()
    # A partial result is not client-downloadable, so refund what was charged —
    # UNLESS the caller keeps the run resumable (e.g. needs_topup), where the
    # client will continue the same paid project after topping up.
    if refund:
        from .token_ledger import refund_project_credits
        r = refund_project_credits(db, project, f"partial: {reason}")
        if r.get("refunded"):
            log_event(db, project.id, "credits_refunded",
                      f"Возврат {r['refunded']} credits: частичный результат не доставлен ({reason})",
                      r, ws)
    log_event(db, project.id, "partial_ready",
              f"Pipeline stopped early ({reason}); partial package assembled", {}, ws)
