import json

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..lib.output_filter import sanitize
from ..lib.security import token_version, verify_token
from ..models import Artifact, Event, Project, ProjectPhase, User
from ..services import budget_engine, credit_pricing, personality
from ..services.project_intake import create_project, workspace_path
from ..services.settings_service import get_setting
from ..services.token_ledger import DEMO_PROJECT_BUDGET_USD, authorize_project_credits
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
    requested_outputs: list[str] = ["mvp", "docs"]
    project_type: str = "auto"
    project_mode: str = "auto"
    technical_level: str = "non_technical"
    personality_mode: str = "balanced"
    user_goal: str = ""


class ContinueBody(BaseModel):
    action: str = Field(min_length=1, max_length=200)
    budget_usd: float | None = None
    budget_credits: int | None = Field(default=None, gt=0, le=10000000)


def _accessible_project(db: Session, project_id: str, user: User) -> Project:
    project = db.get(Project, project_id)
    if not project or project.deleted:
        raise HTTPException(404, "project not found")
    if user.role != "admin" and project.user_id != user.id:
        raise HTTPException(404, "project not found")  # do not leak existence
    return project


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
    budget = None
    if (ws / "budget_state.json").exists():
        budget = budget_engine.load_budget_state(ws)
        if user.role != "admin":
            budget = {
                "user_budget_usd": budget.get("user_budget_usd", float(p.budget_usd)),
                "spent_usd": budget.get("spent_usd", 0),
                "remaining_usd": budget.get("remaining_usd", float(p.budget_usd)),
                "status": budget.get("status", p.status),
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
        # user-facing credit accounting
        "credits_estimate": p.credits_estimate,
        "credits_spent": p.credits_spent,
        "credits_remaining": max((user.token_balance or 0), 0) if user.role != "admin" else None,
        "credits_per_usd": credit_pricing.tokens_per_usd(db),
        "demo_run": p.demo_run,
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
    auth = authorize_project_credits(db, user, phases, body.budget_usd, body.title)
    project = create_project(
        db, body.title, body.brief, body.budget_usd, body.requested_outputs,
        body.project_type, body.project_mode, body.technical_level,
        body.user_goal, user_id=user.id,
        personality_mode=body.personality_mode)
    project.demo_run = auth["demo_run"]
    db.commit()
    log_user_activity(db, user, "project_created", project_id=project.id,
                      meta={"budget_usd": body.budget_usd,
                            "credits_estimate": auth["credits_estimate"],
                            "demo_run": auth["demo_run"]})
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
    if project.status in ("running", "packaging", "queued") and is_running(project_id):
        raise HTTPException(409, "project already running")
    if project.status in ("running", "packaging", "queued"):
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
    auth = authorize_project_credits(db, user, phases, budget_usd,
                                     f"{parent.title} — {body.action}")
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
    db.commit()
    log_user_activity(db, user, "project_continued", project_id=child.id,
                      meta={"parent_project_id": parent.id, "action": body.action,
                            "budget_credits": body.budget_credits,
                            "credits_estimate": auth["credits_estimate"]})
    return {"project_id": child.id, "parent_project_id": parent.id,
            "status": child.status, "credits_estimate": auth["credits_estimate"],
            "surcharge_risk": auth["surcharge_risk"], "demo_run": auth["demo_run"]}


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


@router.get("/{project_id}/artifacts")
def artifacts(project_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    _accessible_project(db, project_id, user)
    q = db.query(Artifact).filter(Artifact.project_id == project_id)
    if user.role != "admin":
        q = q.filter(Artifact.artifact_type == "final")
    rows = q.order_by(Artifact.created_at.asc()).all()
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
    if not str(f).startswith(str(ws.resolve())) or not f.exists():
        raise HTTPException(404, "file not found")
    return a, f


@router.get("/{project_id}/artifacts/{artifact_id}/content")
def artifact_content(project_id: str, artifact_id: str,
                     user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    _accessible_project(db, project_id, user)
    a, f = _artifact_file(db, project_id, artifact_id)
    if user.role != "admin" and a.artifact_type != "final":
        raise HTTPException(404, "artifact not found")
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
    _accessible_project(db, project_id, user)
    a, f = _artifact_file(db, project_id, artifact_id)
    if user.role != "admin" and a.artifact_type != "final":
        raise HTTPException(404, "artifact not found")
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
