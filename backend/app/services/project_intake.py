"""Project Intake Service: create project, workspace, budget state, phase plan."""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import settings
from ..models import Project, ProjectPhase
from . import budget_engine
from .auto_detect import detect
from .event_log import log_event

WORKSPACE_SUBDIRS = ["spec", "architecture", "repo", "reviews", "artifacts", "logs"]


def workspace_path(project_id: str) -> Path:
    return settings.STORAGE_PATH / project_id


def create_project(db: Session, title: str, brief: str, budget_usd: float,
                   requested_outputs: list[str], project_type: str = "auto",
                   project_mode: str = "auto", technical_level: str = "non_technical",
                   user_goal: str = "", user_id: str | None = None,
                   parent_project_id: str | None = None,
                   personality_mode: str = "balanced") -> Project:
    swarm_size, phases = budget_engine.plan_swarm(budget_usd, db)
    complexity = budget_engine.estimate_complexity(brief, budget_usd)
    resolved_type, resolved_mode, requires_codebase = detect(
        db, brief, project_type, project_mode)

    from . import credit_pricing, personality, prompt_guard
    credits_estimate = credit_pricing.estimate(
        phases, budget_usd=budget_usd, db=db)["credits_estimate"]
    injection = prompt_guard.scan(f"{brief}\n{user_goal}")

    project = Project(
        title=title, brief=brief, budget_usd=budget_usd,
        requested_outputs=requested_outputs, project_type=resolved_type,
        project_mode=resolved_mode, requires_codebase=requires_codebase,
        technical_level=technical_level, user_goal=user_goal,
        personality_mode=personality.normalize(personality_mode),
        user_id=user_id, parent_project_id=parent_project_id,
        status="accepted", complexity=complexity, swarm_size=swarm_size,
        current_phase=None, credits_estimate=credits_estimate,
        risk_level=injection["risk_level"],
    )
    db.add(project)
    db.commit()

    ws = workspace_path(project.id)
    for sub in WORKSPACE_SUBDIRS:
        (ws / sub).mkdir(parents=True, exist_ok=True)

    (ws / "brief.md").write_text(f"# {title}\n\n{brief}\n\n"
                                 f"Requested outputs: {', '.join(requested_outputs)}\n"
                                 f"Budget: ${budget_usd}\n")
    budget_engine.save_budget_state(ws, budget_engine.build_budget_state(project.id, budget_usd))

    per_phase = round(budget_engine.load_budget_state(ws)["model_budget_usd"] / max(len(phases), 1), 2)
    phase_plan = {
        "project_id": project.id,
        "phases": [{
            "phase_id": p, "status": "pending",
            "input_artifacts": [], "output_artifacts": [], "assigned_agents": [],
            "budget_limit_usd": per_phase,
            "time_limit_minutes": settings.MAX_PHASE_RUNTIME_MINUTES,
            "exit_criteria": [],
        } for p in phases],
    }
    (ws / "phase_plan.json").write_text(json.dumps(phase_plan, indent=2, ensure_ascii=False))
    (ws / "swarm_state.json").write_text(json.dumps(
        {"swarm_size": swarm_size, "complexity": complexity,
         "project_type": resolved_type, "project_mode": resolved_mode,
         "requires_codebase": requires_codebase}, indent=2))

    for p in phases:
        db.add(ProjectPhase(project_id=project.id, phase_key=p, budget_limit_usd=per_phase))
    db.commit()

    log_event(db, project.id, "project_accepted",
              f"Project accepted: {title}",
              {"swarm_size": swarm_size, "complexity": complexity,
               "project_type": resolved_type, "project_mode": resolved_mode,
               "requires_codebase": requires_codebase}, ws)
    if injection["risk_level"] in ("medium", "high"):
        log_event(db, project.id, "prompt_risk_flagged",
                  f"Бриф отмечен как риск prompt-injection: {injection['risk_level']}",
                  {"risk_level": injection["risk_level"],
                   "categories": injection["categories"]}, ws)
    return project
