import json

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..database import get_db
from ..lib.output_filter import sanitize
from ..lib.security import token_version, verify_token
from ..models import Artifact, Event, Project, ProjectPhase, User
from ..services import budget_engine, credit_pricing, personality
from ..services.project_intake import create_project, workspace_path
from ..services.settings_service import get_setting
from ..services.token_ledger import (
    DEMO_PROJECT_BUDGET_USD,
    authorize_project_credits,
    billing_mode_for,
    uses_client_billing,
)
from ..services.user_activity import log_user_activity
from ..workers.project_worker import enqueue, is_running
from .deps import SESSION_COOKIE, get_current_user

router = APIRouter(prefix="/api/projects", tags=["projects"])

TEXT_DOWNLOAD_SUFFIXES = {".md", ".txt", ".json", ".html", ".css", ".js", ".ts", ".tsx", ".py"}

PUBLIC_EVENT_TYPES = {
    "project_accepted",
    "phase_started",
    "phase_finished",
    "issues_created",
    "issues_repaired",
    "sandbox_run",
    "audit_completed",
    "release_decision",
    "packaged",
    "partial_ready",
}

PUBLIC_PHASE_LABELS = {
    "intake": "Подготовка",
    "swarm_understanding": "Уточнение",
    "spec_war": "План",
    "architecture_battle": "Подход",
    "build_sprint": "Сборка",
    "review_stop": "Контроль",
    "repair_sprint": "Правки",
    "final_audit": "Проверка",
    "packaging": "Пакет",
}


def _public_event_message(event_type: str, message: str) -> str:
    if event_type == "project_accepted":
        return message.replace("Project accepted:", "Проект принят:")
    if event_type == "phase_started":
        return "Начался очередной этап"
    if event_type == "phase_finished":
        return "Этап завершён"
    if event_type == "issues_created":
        return "Проверка нашла замечания"
    if event_type == "issues_repaired":
        return "Часть замечаний обработана"
    if event_type == "sandbox_run":
        return "Автопроверка файлов завершена"
    if event_type == "audit_completed":
        return "Проверка готовности завершена"
    if event_type == "release_decision":
        return "Финальное решение по готовности принято"
    if event_type == "packaged":
        return "Итоговый архив создан"
    if event_type == "partial_ready":
        return "Собран частичный пакет"
    return "Этап обновлён"


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    brief: str = Field(min_length=1, max_length=20000)
    budget_usd: float = Field(gt=0, le=100000)
    requested_outputs: list[str] = Field(default_factory=lambda: ["mvp", "docs"],
                                         max_length=20)
    project_type: str = Field(default="auto", max_length=80)
    project_mode: str = Field(default="auto", max_length=80)
    technical_level: str = Field(default="non_technical", max_length=80)
    personality_mode: str = Field(default="balanced", max_length=80)
    user_goal: str = Field(default="", max_length=1000)
    simulate_client_billing: bool = False
    # fast mode: one coherent model builds the whole project (single_agent)
    # instead of a rotating swarm — a unified result and a much quicker run.
    fast: bool = False

    @field_validator("requested_outputs")
    @classmethod
    def _clean_requested_outputs(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = (raw or "").strip()
            if not value:
                raise ValueError("requested output must not be empty")
            if len(value) > 80:
                raise ValueError("requested output is too long")
            if value not in seen:
                cleaned.append(value)
                seen.add(value)
        return cleaned


class ContinueBody(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    budget_usd: float | None = None
    budget_credits: int | None = Field(default=None, gt=0, le=10000000)
    simulate_client_billing: bool = False


class InstantCreate(BaseModel):
    """The magic button: the client types what they want — nothing else."""
    prompt: str = Field(min_length=10, max_length=20000)


def _instant_title(prompt: str) -> str:
    """A human title out of the prompt: first sentence/line, trimmed."""
    first = prompt.strip().splitlines()[0]
    for stop in (". ", "! ", "? "):
        if stop in first:
            first = first.split(stop)[0]
            break
    first = first.strip().rstrip(".!?…")
    return (first[:77] + "…") if len(first) > 80 else (first or "Новый проект")


def _instant_budget(db: Session, user: User) -> float:
    """Pick the budget FOR the client: the trial for first-timers, otherwise
    the largest package their balance safely covers. 0 → cannot start."""
    from ..models import Tariff
    balance = user.token_balance or 0
    if user.role == "admin":
        return 20.0  # founder test runs bypass billing; a mid-size package
    if (user.demo_generations_remaining or 0) > 0 and balance >= 1:
        return 1.0  # first project rides the trial slot
    prices = [float(t.price_usd) for t in
              db.query(Tariff).filter(Tariff.enabled.is_(True))
              .order_by(Tariff.price_usd.desc()).all()] or [200, 100, 40, 20, 1]
    for price in prices:
        _, phases = budget_engine.plan_swarm(price, db)
        est = credit_pricing.estimate(phases, budget_usd=price, db=db)
        if balance >= est["credits_min"]:
            return price
    return 0.0


def _accessible_project(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted:
        raise HTTPException(404, "project not found")
    if user.role != "admin" and project.user_id != user.id:
        raise HTTPException(404, "project not found")  # do not leak existence
    return project


def _client_release_ok(project: Project) -> bool:
    """A paying client may only receive a final deliverable when the binding
    release gate says so: status == 'ready' AND release_decision == 'release'.
    partial_ready / draft / needs_* are internal states — admin-only (spec §7.10)."""
    return project.status == "ready" and (project.release_decision or "") == "release"


def _enforce_client_release(project: Project, user: User) -> None:
    if user.role == "admin":
        return  # founder may inspect any state for investigation
    if not _client_release_ok(project):
        # 403 (not 404): the project is theirs, it just is not a finished result.
        raise HTTPException(403, {
            "message": "project is not released for download yet",
            "status": project.status,
            "release_decision": project.release_decision or "pending",
        })


def _zero_credit_reason(db: Session, project: Project, owner: User | None) -> str:
    if int(project.credits_spent or 0) > 0:
        return "client_credits_charged"
    mode = billing_mode_for(project, owner)
    if mode == "admin_bypass":
        return "admin_bypass"
    if owner is None:
        return "missing_owner"
    phases = db.query(ProjectPhase).filter(ProjectPhase.project_id == project.id).all()
    if not phases:
        return "not_started"
    if any((p.credits_charged or 0) > 0 for p in phases):
        return "credits_recording_mismatch"
    if not any(bool(p.made_progress) for p in phases):
        return "no_chargeable_progress"
    if project.status in {"accepted", "queued", "running", "packaging", "repairing"}:
        return "not_finished_yet"
    if project.status == "needs_topup":
        return "insufficient_client_credits"
    if _client_release_ok(project):
        return "billing_error_candidate"
    return "not_released_to_client"


def _download_user(db: Session, authorization: str, session_cookie: str = "") -> User:
    """Authenticate downloads via HttpOnly cookie or Authorization header.

    Tokens are never accepted in query params: URLs land in server logs,
    browser history and referrers."""
    raw = ""
    if authorization.startswith("Bearer "):
        raw = authorization.removeprefix("Bearer ").strip()
    elif session_cookie:
        raw = session_cookie
    user_id = verify_token(raw) if raw else None
    user = db.get(User, user_id) if user_id else None
    if not user or user.disabled:
        raise HTTPException(401, "not authenticated")
    if token_version(raw) != (user.token_version or 0):
        raise HTTPException(401, "session revoked")
    return user


def _serialize(db: Session, p: Project, user: User) -> dict:
    ws = workspace_path(p.id)
    owner = db.get(User, p.user_id) if p.user_id else None
    billing_mode = billing_mode_for(p, owner)
    zero_credit_reason = _zero_credit_reason(db, p, owner)
    budget = None
    if (ws / "budget_state.json").exists():
        budget = budget_engine.load_budget_state(ws)
        if user.role != "admin":
            # The client economy is credits, full stop: the paid package, the
            # credits it granted, and how many burned. Raw internal model spend
            # (provider USD cost) is the platform's cost line — admin-only.
            per_usd = max(credit_pricing.tokens_per_usd(db), 1)
            allocated = int(p.credits_estimate or 0)
            spent_credits = int(p.credits_spent or 0)
            spent_usd_value = round(spent_credits / per_usd, 2)
            budget = {
                "user_budget_usd": float(p.budget_usd),
                "spent_usd": spent_usd_value,
                "remaining_usd": round(max(float(p.budget_usd) - spent_usd_value, 0), 2),
                "status": budget.get("status", p.status),
                "credits_allocated": allocated,
                "credits_spent": spent_credits,
                "credits_remaining_in_package": max(allocated - spent_credits, 0),
            }
    payload = {
        "project_id": p.id, "title": p.title, "brief": p.brief,
        "budget_usd": float(p.budget_usd), "requested_outputs": p.requested_outputs,
        "project_type": p.project_type, "project_mode": p.project_mode,
        "requires_codebase": p.requires_codebase,
        "technical_level": p.technical_level, "user_goal": p.user_goal,
        "personality_mode": getattr(p, "personality_mode", "balanced"),
        "parent_project_id": p.parent_project_id,
        "status": p.status,
        "estimated_complexity": p.complexity,
        "estimated_workflow_size": "standard" if user.role != "admin" else "internal",
        "current_phase": p.current_phase, "budget": budget,
        "risk_level": getattr(p, "risk_level", "low"),
        # release gate: the frontend uses `downloadable` to decide whether to
        # offer the ZIP. Only a released, ready project is downloadable by a client.
        "downloadable": _client_release_ok(p) if user.role != "admin" else True,
        "release_decision": p.release_decision,
        # user-facing credit accounting
        "credits_estimate": p.credits_estimate,
        "credits_spent": p.credits_spent,
        "credits_remaining": max((user.token_balance or 0), 0) if user.role != "admin" else None,
        "credits_per_usd": credit_pricing.tokens_per_usd(db),
        "demo_run": p.demo_run,
        "billing_mode": billing_mode,
        "client_billing_enabled": uses_client_billing(p, owner),
        "zero_credit_reason": zero_credit_reason,
        "billing_note": p.billing_note or "",
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
    if user.role == "admin":
        # founder view: real cost + margin under the credit abstraction
        usd_cost = float(p.estimated_usd_cost or 0)
        credit_value_usd = credit_pricing.credits_to_usd(db, p.credits_spent)
        payload["estimated_swarm_size"] = p.swarm_size
        payload["internal"] = {
            "estimated_usd_cost": round(usd_cost, 6),
            "credits_charged_usd_value": credit_value_usd,
            "platform_margin_usd": round(credit_value_usd - usd_cost, 6),
            "billing_mode": billing_mode,
            "zero_credit_reason": zero_credit_reason,
        }
    return payload


@router.get("/personality-modes")
def personality_modes(user: User = Depends(get_current_user)):
    """Swarm build-style presets for the new-project form."""
    return personality.list_public()


class EstimateRequest(BaseModel):
    budget_usd: float = Field(gt=0, le=100000)


@router.post("/estimate")
def estimate(body: EstimateRequest, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """Pre-run quote: itemized per-phase credits, total range, and how likely the
    user is to need a top-up given their balance."""
    _, phases = budget_engine.plan_swarm(body.budget_usd, db)
    est = credit_pricing.estimate(phases, budget_usd=body.budget_usd, db=db)
    balance = user.token_balance or 0
    demo_eligible = (user.role != "admin"
                     and body.budget_usd <= DEMO_PROJECT_BUDGET_USD
                     and (user.demo_generations_remaining or 0) > 0)
    return {
        **est,
        "token_balance": balance,
        "demo_eligible": demo_eligible,
        "surcharge_risk": "low" if demo_eligible
        else credit_pricing.surcharge_risk(est["credits_max"], balance),
    }


@router.post("")
def create(body: ProjectCreate, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    _, phases = budget_engine.plan_swarm(body.budget_usd, db)
    simulate = user.role == "admin" and body.simulate_client_billing
    auth = authorize_project_credits(db, user, phases, body.budget_usd, body.title,
                                     simulate_client_billing=simulate)
    project = create_project(
        db, body.title, body.brief, body.budget_usd, body.requested_outputs,
        body.project_type, body.project_mode, body.technical_level,
        body.user_goal, user_id=user.id,
        personality_mode=body.personality_mode)
    project.demo_run = auth["demo_run"]
    project.billing_mode = auth.get("billing_mode", "client")
    project.billing_note = auth.get("billing_note", "")
    if body.fast:
        project.execution_mode = "single_agent"
    db.commit()
    log_user_activity(db, user, "project_created", project_id=project.id,
                      meta={"budget_usd": body.budget_usd,
                            "credits_estimate": auth["credits_estimate"],
                            "demo_run": auth["demo_run"],
                            "billing_mode": project.billing_mode})
    return {"project_id": project.id, "status": project.status,
            "estimated_complexity": project.complexity,
            "estimated_workflow_size": "standard",
            "project_mode": project.project_mode,
            "requires_codebase": project.requires_codebase,
            "credits_estimate": auth["credits_estimate"],
            "credits_min": auth["credits_min"],
            "credits_max": auth["credits_max"],
            "surcharge_risk": auth["surcharge_risk"],
            "demo_run": auth["demo_run"],
            "billing_mode": project.billing_mode,
            "admin_bypass": auth.get("admin_bypass", False),
            "token_balance": user.token_balance}


@router.post("/instant")
def instant_create(body: InstantCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """No-code flow: one prompt, one button. The platform derives the title,
    picks the budget/package, auto-detects the project type and starts the
    pipeline immediately — the client only waits for `ready` and downloads."""
    prompt = body.prompt.strip()
    budget_usd = _instant_budget(db, user)
    if budget_usd <= 0:
        raise HTTPException(402, {
            "message": "not enough SwarmBuild credits to start a project",
            "token_balance": user.token_balance or 0,
        })
    _, phases = budget_engine.plan_swarm(budget_usd, db)
    auth = authorize_project_credits(db, user, phases, budget_usd,
                                     _instant_title(prompt))
    project = create_project(
        db, _instant_title(prompt), prompt, budget_usd, ["mvp", "docs"],
        "auto", "auto", "non_technical",
        "Готовый проект под ключ: скачать и пользоваться без доработок.",
        user_id=user.id)
    project.demo_run = auth["demo_run"]
    # the one-button flow is the "just make it" path: run in fast mode so the
    # client gets ONE coherent, runnable project (single model) instead of a
    # swarm of fragments, and gets it quickly.
    project.execution_mode = "single_agent"
    project.status = "queued"
    db.commit()
    log_user_activity(db, user, "project_created_instant", project_id=project.id,
                      meta={"budget_usd": budget_usd,
                            "credits_estimate": auth["credits_estimate"],
                            "demo_run": auth["demo_run"]})
    enqueue(project.id)
    return {"project_id": project.id, "status": "queued",
            "title": project.title, "budget_usd": budget_usd,
            "credits_estimate": auth["credits_estimate"],
            "demo_run": auth["demo_run"],
            "token_balance": user.token_balance}


@router.get("")
def list_projects(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(Project).filter(Project.deleted.is_(False))
    if user.role != "admin":
        q = q.filter(Project.user_id == user.id)
    return [_serialize(db, p, user) for p in q.order_by(Project.created_at.desc()).all()]


@router.get("/{project_id}")
def get_project(project_id: str, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    return _serialize(db, _accessible_project(db, project_id, user), user)


@router.post("/{project_id}/start")
def start(project_id: str, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    project = _accessible_project(db, project_id, user)
    if project.status in ("running", "packaging", "queued", "repairing") and is_running(project_id):
        raise HTTPException(409, "project already running")
    if project.status in ("running", "packaging", "queued", "repairing"):
        log_user_activity(db, user, "stale_project_resumed", project_id=project_id,
                          meta={"previous_status": project.status,
                                "current_phase": project.current_phase})
    project.status = "queued"
    db.commit()
    log_user_activity(db, user, "project_started", project_id=project_id)
    enqueue(project_id)
    return {"project_id": project_id, "status": "queued"}


@router.post("/{project_id}/cancel")
def cancel(project_id: str, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    project = _accessible_project(db, project_id, user)
    project.status = "cancelled"
    db.commit()
    return {"project_id": project_id, "status": "cancelled"}


@router.post("/{project_id}/continue")
def continue_project(project_id: str, body: ContinueBody,
                     user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Spec-2 §8/§16: continue/improve creates a linked child project."""
    parent = _accessible_project(db, project_id, user)
    per_usd = int(get_setting(db, "tokens_per_usd") or 100)
    budget_usd = (
        body.budget_credits / per_usd
        if body.budget_credits is not None
        else body.budget_usd or float(parent.budget_usd)
    )
    _, phases = budget_engine.plan_swarm(budget_usd, db)
    simulate = user.role == "admin" and body.simulate_client_billing
    auth = authorize_project_credits(db, user, phases, budget_usd,
                                     f"{parent.title} — {body.action}",
                                     simulate_client_billing=simulate)
    child = create_project(
        db,
        title=f"{parent.title} — {body.action}",
        brief=f"Доработка существующего проекта «{parent.title}».\n\n"
              f"Задача: {body.action}\n\nИсходный бриф:\n{parent.brief}",
        budget_usd=budget_usd,
        requested_outputs=parent.requested_outputs,
        project_type=parent.project_type, project_mode=parent.project_mode,
        technical_level=parent.technical_level, user_goal=body.action,
        user_id=user.id, parent_project_id=parent.id,
        personality_mode=getattr(parent, "personality_mode", "balanced"))
    child.demo_run = auth["demo_run"]
    child.billing_mode = auth.get("billing_mode", "client")
    child.billing_note = auth.get("billing_note", "")
    db.commit()
    log_user_activity(db, user, "project_continued", project_id=child.id,
                      meta={"parent_project_id": parent.id, "action": body.action,
                            "budget_credits": body.budget_credits,
                            "credits_estimate": auth["credits_estimate"],
                            "billing_mode": child.billing_mode})
    return {"project_id": child.id, "parent_project_id": parent.id,
            "status": child.status, "credits_estimate": auth["credits_estimate"],
            "surcharge_risk": auth["surcharge_risk"], "demo_run": auth["demo_run"],
            "billing_mode": child.billing_mode,
            "admin_bypass": auth.get("admin_bypass", False)}


@router.get("/{project_id}/events")
def events(project_id: str, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    _accessible_project(db, project_id, user)
    q = db.query(Event).filter(Event.project_id == project_id)
    if user.role != "admin":
        q = q.filter(Event.event_type.in_(PUBLIC_EVENT_TYPES))
    rows = q.order_by(Event.created_at.asc()).all()
    return [{
        "type": e.event_type,
        "message": e.message if user.role == "admin" else _public_event_message(e.event_type, e.message),
        "metadata": e.meta if user.role == "admin" else {},
        "created_at": e.created_at.isoformat(),
    } for e in rows]


@router.get("/{project_id}/phases")
def phases(project_id: str, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    _accessible_project(db, project_id, user)
    ws = workspace_path(project_id)
    order: list[str] = []
    if (ws / "phase_plan.json").exists():
        order = [p["phase_id"] for p in json.loads((ws / "phase_plan.json").read_text())["phases"]]
    rows = db.query(ProjectPhase).filter(ProjectPhase.project_id == project_id).all()
    rows.sort(key=lambda r: order.index(r.phase_key) if r.phase_key in order else 99)
    return [{"phase_key": r.phase_key if user.role == "admin" else f"stage_{i + 1}",
             "label": PUBLIC_PHASE_LABELS.get(r.phase_key, "Этап"),
             "status": r.status,
             "budget_limit_usd": float(r.budget_limit_usd),
             "spent_estimated_usd": float(r.spent_estimated_usd) if user.role == "admin" else 0,
             "decision": r.decision if user.role == "admin" else None,
             "started_at": r.started_at.isoformat() if r.started_at else None,
             "finished_at": r.finished_at.isoformat() if r.finished_at else None}
            for i, r in enumerate(rows)]


# The client-facing "final files" list is deliberately lean: the packaged
# archive (which already contains every supporting doc) plus the single primary
# deliverable. Business-plan/pitch-deck/limitations/etc. still ship INSIDE the
# zip, they just do not clutter the top-level list. Admins can pass `?full=1`
# to see every artifact (including internal phase outputs) for diagnostics.
_HEADLINE_ARTIFACTS = ("project.zip", "README.md", "main-document.md")


@router.get("/{project_id}/artifacts")
def artifacts(project_id: str, full: bool = False,
              user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    _accessible_project(db, project_id, user)
    rows = (db.query(Artifact).filter(Artifact.project_id == project_id)
            .order_by(Artifact.created_at.asc()).all())
    if not (full and user.role == "admin"):
        rows = [a for a in rows
                if a.artifact_type == "final" and a.display_name in _HEADLINE_ARTIFACTS]
        # keep a stable, meaningful order: archive first, then the main document
        rows.sort(key=lambda a: _HEADLINE_ARTIFACTS.index(a.display_name)
                  if a.display_name in _HEADLINE_ARTIFACTS else 99)
    return [{"id": a.id, "artifact_type": a.artifact_type, "path": a.path,
             "display_name": a.display_name,
             "safety_status": getattr(a, "safety_status", "safe_to_download")} for a in rows]


def _enforce_downloadable(a: Artifact, user: User) -> None:
    """Blocked artifacts are only reachable by admins (for investigation)."""
    if getattr(a, "safety_status", "safe_to_download") == "blocked" and user.role != "admin":
        raise HTTPException(403, "artifact blocked by security scan")


def _artifact_file(db: Session, project_id: str, artifact_id: str):
    a = db.get(Artifact, artifact_id)
    if not a or a.project_id != project_id:
        raise HTTPException(404, "artifact not found")
    ws = workspace_path(project_id)
    f = (ws / a.path).resolve()
    # Path-component containment (not a string prefix): a bare startswith would
    # accept a sibling workspace sharing the same prefix (…/ws-evil vs …/ws).
    if not f.is_relative_to(ws.resolve()) or not f.exists():
        raise HTTPException(404, "file not found")
    return a, f


@router.get("/{project_id}/artifacts/{artifact_id}/content")
def artifact_content(project_id: str, artifact_id: str,
                     user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    project = _accessible_project(db, project_id, user)
    a, f = _artifact_file(db, project_id, artifact_id)
    if user.role != "admin" and a.artifact_type != "final":
        raise HTTPException(404, "artifact not found")
    _enforce_client_release(project, user)
    if f.suffix == ".zip":
        raise HTTPException(400, "use the download endpoint for archives")
    log_user_activity(db, user, "artifact_viewed", project_id=project_id,
                      meta={"artifact_id": artifact_id, "path": a.path})
    content = f.read_text(errors="replace")
    if user.role != "admin":
        content = sanitize(content)[0]
    return {"path": a.path, "content": content}


@router.get("/{project_id}/artifacts/{artifact_id}/download")
def artifact_download(project_id: str, artifact_id: str,
                      authorization: str = Header(default=""),
                      sb_session: str = Cookie(default="", alias=SESSION_COOKIE),
                      db: Session = Depends(get_db)):
    user = _download_user(db, authorization, sb_session)
    project = _accessible_project(db, project_id, user)
    a, f = _artifact_file(db, project_id, artifact_id)
    if user.role != "admin" and a.artifact_type != "final":
        raise HTTPException(404, "artifact not found")
    _enforce_client_release(project, user)
    _enforce_downloadable(a, user)
    action = "artifact_downloaded_by_admin" if user.role == "admin" else "artifact_downloaded"
    log_user_activity(db, user, action, project_id=project_id,
                      meta={"artifact_id": artifact_id, "path": a.path})
    if user.role != "admin" and f.suffix.lower() in TEXT_DOWNLOAD_SUFFIXES:
        content = sanitize(f.read_text(errors="replace"))[0]
        return Response(
            content,
            media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{f.name}"'},
        )
    return FileResponse(f, filename=f.name)


@router.get("/{project_id}/download")
def download(project_id: str, authorization: str = Header(default=""),
             sb_session: str = Cookie(default="", alias=SESSION_COOKIE),
             db: Session = Depends(get_db)):
    user = _download_user(db, authorization, sb_session)
    project = _accessible_project(db, project_id, user)
    # The binding release gate: a paying client only gets project.zip as a final
    # deliverable when it is genuinely ready and released. Partial/draft/failed
    # archives are admin-only, so an unfinished build can never be handed over.
    _enforce_client_release(project, user)
    zip_path = workspace_path(project_id) / "artifacts" / "project.zip"
    if not zip_path.exists():
        raise HTTPException(404, "archive not ready yet")
    zip_art = (db.query(Artifact).filter(Artifact.project_id == project_id,
               Artifact.display_name == "project.zip").first())
    if zip_art:
        _enforce_downloadable(zip_art, user)
    action = "project_zip_downloaded_by_admin" if user.role == "admin" else "project_zip_downloaded"
    log_user_activity(db, user, action, project_id=project_id)
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in project.title)[:40]
    return FileResponse(zip_path, media_type="application/zip",
                        filename=f"{safe_title or 'project'}.zip")
