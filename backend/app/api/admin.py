import ipaddress
import json
import socket
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..lib.redact import redact_error, redact_text
from ..models import (
    AgentCall,
    CreditTopup,
    Issue,
    ModelEntry,
    Project,
    ProjectPhase,
    ProjectType,
    Provider,
    ProviderKey,
    Tariff,
    User,
    UserActivity,
)
from ..providers import get_provider
from ..services import credit_pricing, key_pool
from ..services.artifact_packager import package
from ..services.project_intake import workspace_path
from ..services.settings_service import all_settings, get_setting, set_setting
from ..services.token_ledger import billing_mode_for, uses_client_billing
from ..services.user_activity import log_user_activity
from ..workers.project_worker import enqueue
from .deps import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"],
                   dependencies=[Depends(require_admin)])


def _audit(db: Session, admin: User, action: str, **meta) -> None:
    """Record an admin action to the audit trail (never includes secrets)."""
    log_user_activity(db, admin, f"admin_{action}", meta=meta)


# --- dashboard ---------------------------------------------------------------

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    projects = db.query(Project).filter(Project.deleted.is_(False))
    project_rows = projects.all()
    owner_ids = {p.user_id for p in project_rows if p.user_id}
    owners = {}
    if owner_ids:
        owners = {u.id: u for u in db.query(User).filter(User.id.in_(owner_ids)).all()}
    billing_modes = {p.id: billing_mode_for(p, owners.get(p.user_id)) for p in project_rows}
    admin_bypass_projects = sum(1 for p in project_rows if billing_modes[p.id] == "admin_bypass")
    client_simulation_projects = sum(1 for p in project_rows if billing_modes[p.id] == "client_simulation")
    client_billed_projects = sum(1 for p in project_rows if billing_modes[p.id] in {"client", "client_simulation"})
    client_zero_credit_projects = sum(
        1 for p in project_rows
        if billing_modes[p.id] in {"client", "client_simulation"}
        and int(p.credits_spent or 0) == 0
        and p.status not in {"accepted", "queued", "running", "packaging", "repairing", "cancelled"}
    )
    released_zero_credit_projects = sum(
        1 for p in project_rows
        if billing_modes[p.id] in {"client", "client_simulation"}
        and int(p.credits_spent or 0) == 0
        and p.status == "ready"
        and p.release_decision == "release"
    )
    by_status = dict(db.query(Project.status, func.count())
                     .filter(Project.deleted.is_(False)).group_by(Project.status).all())
    total_spend = db.query(func.sum(AgentCall.cost_estimated_usd)).scalar() or 0
    credits_granted = db.query(func.sum(User.lifetime_tokens_granted)).scalar() or 0
    credits_spent = db.query(func.sum(User.lifetime_tokens_spent)).scalar() or 0
    outstanding_credits = db.query(func.sum(User.token_balance)).scalar() or 0
    topups_pending = db.query(CreditTopup).filter(CreditTopup.status == "pending").count()
    topups_paid_usd = db.query(func.sum(CreditTopup.amount_usd)).filter(
        CreditTopup.status == "paid").scalar() or 0
    credits_spent_usd = credit_pricing.credits_to_usd(db, credits_spent)
    return {
        "projects_total": len(project_rows),
        "projects_ready": by_status.get("ready", 0),
        "projects_partial_ready": by_status.get("partial_ready", 0),
        "projects_failed": by_status.get("failed", 0),
        "projects_running": by_status.get("running", 0) + by_status.get("queued", 0),
        "estimated_spend_usd": round(float(total_spend), 6),
        "credits_per_usd": credit_pricing.tokens_per_usd(db),
        "credits_spent": int(credits_spent),
        "credits_granted": int(credits_granted),
        "outstanding_credits": int(outstanding_credits),
        "credits_spent_usd_value": credits_spent_usd,
        "gross_margin_usd": round(credits_spent_usd - float(total_spend), 6),
        "admin_bypass_projects": admin_bypass_projects,
        "client_billed_projects": client_billed_projects,
        "client_simulation_projects": client_simulation_projects,
        "client_zero_credit_projects": client_zero_credit_projects,
        "released_zero_credit_projects": released_zero_credit_projects,
        "zero_credit_status": (
            "billing_error"
            if released_zero_credit_projects else
            "admin_bypass_only"
            if admin_bypass_projects and not client_zero_credit_projects else
            "ok"
        ),
        "topups_pending": topups_pending,
        "topups_paid_usd": round(float(topups_paid_usd), 2),
        "users_total": db.query(User).count(),
        "user_activity_events": db.query(UserActivity).count(),
        "providers_active": db.query(Provider).filter(Provider.enabled.is_(True)).count(),
        "models_active": db.query(ModelEntry).filter(ModelEntry.enabled.is_(True)).count(),
    }


# --- projects ----------------------------------------------------------------

@router.get("/projects")
def all_projects(db: Session = Depends(get_db)):
    rows = (db.query(Project, User).outerjoin(User, Project.user_id == User.id)
            .filter(Project.deleted.is_(False))
            .order_by(Project.created_at.desc()).all())
    return [{
        "project_id": p.id, "title": p.title, "user_email": u.email if u else None,
        "status": p.status, "budget_usd": float(p.budget_usd),
        "project_type": p.project_type, "project_mode": p.project_mode,
        "current_phase": p.current_phase,
        "release_decision": p.release_decision,
        "not_released_reason": p.not_released_reason or "",
        "credits_spent": p.credits_spent,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    } for p, u in rows]


@router.get("/projects/{project_id}/integrity")
def project_integrity(project_id: str, db: Session = Depends(get_db)):
    """Founder-only honest picture of a project: token spend, per-phase progress
    proof, deterministic gate failures, and exactly why (if) it was not released
    to the client (spec §7.7–7.10)."""
    project = _project_or_404(db, project_id)
    ws = workspace_path(project_id)
    phases = (db.query(ProjectPhase)
              .filter(ProjectPhase.project_id == project_id).all())
    calls = db.query(AgentCall).filter(AgentCall.project_id == project_id).all()
    real_calls = [c for c in calls if c.status != "provider_error"]
    usd_spend = round(sum(float(c.cost_estimated_usd) for c in calls), 6)
    owner = db.get(User, project.user_id) if project.user_id else None
    billing_mode = billing_mode_for(project, owner)

    release = {}
    rel_path = ws / "reviews" / "release-decision.json"
    if rel_path.exists():
        try:
            release = json.loads(rel_path.read_text())
        except (OSError, json.JSONDecodeError):
            release = {}

    open_issues = db.query(Issue).filter(Issue.project_id == project_id,
                                         Issue.status == "open").all()
    gate_issues = [i for i in open_issues if i.title.startswith("GATE-")]

    return {
        "project_id": project.id,
        "status": project.status,
        "release_decision": project.release_decision,
        "released_to_client": project.status == "ready" and project.release_decision == "release",
        "not_released_reason": project.not_released_reason or "",
        "token_spend": {
            "usd_cost_estimated": usd_spend,
            "credits_spent": project.credits_spent,
            "credits_spent_usd_value": credit_pricing.credits_to_usd(db, project.credits_spent),
            "billing_mode": billing_mode,
            "client_billing_enabled": uses_client_billing(project, owner),
            "zero_credit_reason": (
                "client_credits_charged" if int(project.credits_spent or 0) > 0
                else "admin_bypass" if billing_mode == "admin_bypass"
                else "billing_error_candidate" if project.status == "ready" and project.release_decision == "release"
                else "no_client_charge_yet"
            ),
            "agent_calls_total": len(calls),
            "agent_calls_failed": len(calls) - len(real_calls),
        },
        "progress_proof": [{
            "phase_key": ph.phase_key,
            "status": ph.status,
            "made_progress": bool(ph.made_progress),
            "credits_charged": ph.credits_charged or 0,
            "zero_charge_reason": (
                "client_credits_charged" if (ph.credits_charged or 0) > 0
                else "admin_bypass" if billing_mode == "admin_bypass"
                else "no_chargeable_progress" if not ph.made_progress
                else "not_charged_yet" if ph.status != "done"
                else "billing_error_candidate"
            ),
            "proof": ph.progress_proof or {},
        } for ph in phases],
        "gate_failures": release.get("gate_failures", []),
        "gates": release.get("gates", {}),
        "open_gate_issues": [{"title": i.title, "severity": i.severity,
                              "description": i.description} for i in gate_issues],
        "notes": release.get("notes", []),
    }


def _project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "project not found")
    return project


def _tail_jsonl(path: Path, limit: int) -> list[dict]:
    if not path.exists():
        return []
    rows: deque[dict] = deque(maxlen=limit)
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(rows)


def _preview_text(workspace: Path, rel_path: str | None, limit: int = 1200) -> str | None:
    if not rel_path:
        return None
    ws = workspace.resolve()
    f = (workspace / rel_path).resolve()
    if not str(f).startswith(str(ws)) or not f.exists():
        return None
    try:
        text = redact_text(f.read_text(errors="replace")).strip()
    except OSError:
        return None
    if len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


@router.post("/projects/{project_id}/rerun-phase")
def rerun(project_id: str, db: Session = Depends(get_db),
          admin: User = Depends(require_admin)):
    project = _project_or_404(db, project_id)
    project.status = "queued"
    db.commit()
    enqueue(project_id)
    _audit(db, admin, "project_rerun", project_id=project_id)
    return {"status": "queued"}


@router.post("/projects/{project_id}/force-package")
def force_package(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    _, decision = package(db, project, workspace_path(project_id))
    project.release_decision = decision["decision"]
    project.status = "ready" if decision["decision"] == "release" else "partial_ready"
    if decision["decision"] != "release":
        project.not_released_reason = ("not released: "
                                       + "; ".join(decision.get("notes", [])[:6]))
    db.commit()
    return {"status": project.status, "decision": decision}


@router.post("/projects/{project_id}/status")
def set_status(project_id: str, body: dict, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    status = body.get("status", "")
    if status not in ("ready", "partial_ready", "failed", "cancelled", "draft"):
        raise HTTPException(400, "unsupported status")
    project.status = status
    # Keep the release gate consistent with an explicit founder override so a
    # manually-set "ready" is actually downloadable (and only then).
    if status == "ready":
        project.release_decision = "release"
        project.not_released_reason = ""
    elif status == "partial_ready":
        project.release_decision = "partial_release"
        project.not_released_reason = "manually set to partial by admin"
    db.commit()
    return {"status": status}


@router.delete("/projects/{project_id}")
def soft_delete(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    project.deleted = True
    db.commit()
    return {"deleted": True}


# --- users -------------------------------------------------------------------

@router.get("/users")
def users(db: Session = Depends(get_db)):
    counts = dict(db.query(Project.user_id, func.count())
                  .group_by(Project.user_id).all())
    budgets = dict(db.query(Project.user_id, func.sum(Project.budget_usd))
                   .group_by(Project.user_id).all())
    return [{
        "id": u.id, "email": u.email, "role": u.role, "disabled": u.disabled,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "projects_count": counts.get(u.id, 0),
        "total_budget_usd": float(budgets.get(u.id) or 0),
        "token_balance": u.token_balance or 0,
        "lifetime_tokens_spent": u.lifetime_tokens_spent or 0,
        "demo_generations_remaining": u.demo_generations_remaining or 0,
    } for u in db.query(User).order_by(User.created_at.asc()).all()]


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == "admin", User.disabled.is_(False)).count()


@router.post("/users/{user_id}/role")
def change_role(user_id: str, body: dict, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    if body.get("role") not in ("user", "admin"):
        raise HTTPException(400, "role must be user|admin")
    if user.role == "admin" and body["role"] != "admin" and _active_admin_count(db) <= 1:
        raise HTTPException(400, "cannot demote the last active admin")
    user.role = body["role"]
    db.commit()
    return {"role": user.role}


@router.post("/users/{user_id}/disable")
def toggle_disable(user_id: str, body: dict, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "user not found")
    disabled = bool(body.get("disabled", True))
    if user.role == "admin" and disabled and _active_admin_count(db) <= 1:
        raise HTTPException(400, "cannot disable the last active admin")
    user.disabled = disabled
    db.commit()
    return {"disabled": user.disabled}


# --- providers ---------------------------------------------------------------

class ProviderBody(BaseModel):
    name: str
    provider_type: str
    base_url: str = ""
    api_key: str = ""
    enabled: bool = True
    priority: int = 100
    notes: str = ""


def _is_private_host(host: str) -> bool:
    clean = host.strip().strip("[]").lower()
    if clean in {"localhost", "metadata.google.internal"} or clean.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(clean)
        return any((ip.is_private, ip.is_loopback, ip.is_link_local,
                    ip.is_multicast, ip.is_reserved, ip.is_unspecified))
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(clean, None)
    except socket.gaierror as exc:
        raise HTTPException(400, "base_url host cannot be resolved") from exc
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if any((ip.is_private, ip.is_loopback, ip.is_link_local,
                ip.is_multicast, ip.is_reserved, ip.is_unspecified)):
            return True
    return False


def _validate_base_url(base_url: str, db: Session) -> None:
    """Only allow http(s) endpoints — the adapters feed base_url straight into
    urllib, so file:// / gopher:// etc. must not be reachable via a provider."""
    if not base_url:
        return
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(400, "base_url must be an http(s) URL")
    if parsed.username or parsed.password:
        raise HTTPException(400, "base_url must not contain credentials")
    if parsed.scheme != "https" and not get_setting(db, "allow_insecure_provider_urls"):
        raise HTTPException(400, "base_url must use https")
    host = parsed.hostname or ""
    if _is_private_host(host) and not get_setting(db, "allow_private_provider_urls"):
        raise HTTPException(400, "private provider URLs are disabled")


def _provider_out(p: Provider, db: Session | None = None) -> dict:
    key_count = 0
    active_keys = 0
    errored_keys = 0
    total_key_uses = 0
    mask = p.api_key_mask
    if db is not None:
        key_count = db.query(ProviderKey).filter(ProviderKey.provider_id == p.id).count()
        active_keys = key_pool.usable_key_count(db, p)
        errored_keys = (db.query(ProviderKey)
                        .filter(ProviderKey.provider_id == p.id,
                                ProviderKey.enabled.is_(True),
                                ProviderKey.status == "error").count())
        total_key_uses = (db.query(func.sum(ProviderKey.use_count))
                          .filter(ProviderKey.provider_id == p.id).scalar() or 0)
        if not mask:  # keys live in the pool — show the newest key's mask as representative
            newest = (db.query(ProviderKey).filter(ProviderKey.provider_id == p.id)
                      .order_by(ProviderKey.created_at.desc()).first())
            if newest:
                mask = newest.api_key_mask
    return {"id": p.id, "name": p.name, "provider_type": p.provider_type,
            "base_url": p.base_url, "api_key_mask": mask,
            "has_key": bool(p.api_key_encrypted) or key_count > 0,
            "key_count": key_count, "active_keys": active_keys,
            "errored_keys": errored_keys, "total_key_uses": int(total_key_uses),
            "enabled": p.enabled, "priority": p.priority, "status": p.status,
            "last_tested_at": p.last_tested_at.isoformat() if p.last_tested_at else None,
            "last_error": p.last_error, "notes": p.notes}


@router.get("/providers")
def providers(db: Session = Depends(get_db)):
    return [_provider_out(p, db) for p in
            db.query(Provider).order_by(Provider.priority.asc()).all()]


@router.get("/runtime")
def runtime(db: Session = Depends(get_db)):
    providers = db.query(Provider).filter(Provider.enabled.is_(True)).all()
    real_providers = [p for p in providers if p.provider_type != "mock"]
    usable_key_total = sum(key_pool.usable_key_count(db, p) for p in real_providers)
    enabled_real_models = (db.query(ModelEntry)
                           .join(Provider, ModelEntry.provider_id == Provider.id)
                           .filter(ModelEntry.enabled.is_(True),
                                   Provider.enabled.is_(True),
                                   Provider.provider_type != "mock")
                           .count())
    recent_errors = (db.query(AgentCall)
                     .filter(AgentCall.status == "provider_error")
                     .order_by(AgentCall.created_at.desc())
                     .limit(5).all())
    return {
        "enable_real_model_calls": bool(get_setting(db, "enable_real_model_calls")),
        "enable_mock_mode": bool(get_setting(db, "enable_mock_mode")),
        "allow_mock_fallback": bool(get_setting(db, "allow_mock_fallback")),
        "execution_mode": str(get_setting(db, "execution_mode") or "swarm"),
        "usable_real_keys": usable_key_total,
        "enabled_real_models": enabled_real_models,
        "real_providers_ready": sum(1 for p in real_providers
                                    if key_pool.usable_key_count(db, p) > 0),
        "recent_provider_errors": [{
            "project_id": c.project_id,
            "provider_type": getattr(c, "provider_type", ""),
            "provider_model_name": getattr(c, "provider_model_name", ""),
            "provider_key_mask": getattr(c, "provider_key_mask", ""),
            "error_message": getattr(c, "error_message", ""),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        } for c in recent_errors],
    }


@router.post("/providers")
def create_provider(body: ProviderBody, db: Session = Depends(get_db),
                    admin: User = Depends(require_admin)):
    _validate_base_url(body.base_url, db)
    p = Provider(name=body.name, provider_type=body.provider_type,
                 base_url=body.base_url, enabled=body.enabled,
                 priority=body.priority, notes=body.notes)
    db.add(p)
    db.commit()
    if body.api_key:  # seed the pool with the first key
        key_pool.add_keys(db, p, body.api_key)
    _audit(db, admin, "provider_created", provider_id=p.id, name=p.name,
           provider_type=p.provider_type)
    return _provider_out(p, db)


@router.put("/providers/{provider_id}")
def update_provider(provider_id: str, body: ProviderBody, db: Session = Depends(get_db),
                    admin: User = Depends(require_admin)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "provider not found")
    _validate_base_url(body.base_url, db)
    p.name, p.provider_type, p.base_url = body.name, body.provider_type, body.base_url
    p.enabled, p.priority, p.notes = body.enabled, body.priority, body.notes
    if body.api_key:  # append to the pool (bulk paste supported)
        key_pool.add_keys(db, p, body.api_key)
        p.status = "untested"
    db.commit()
    _audit(db, admin, "provider_updated", provider_id=p.id, name=p.name,
           enabled=p.enabled, key_replaced=bool(body.api_key))
    return _provider_out(p, db)


@router.delete("/providers/{provider_id}/key")
def delete_provider_key(provider_id: str, db: Session = Depends(get_db),
                        admin: User = Depends(require_admin)):
    """Clears the whole key pool (and any legacy single key) for a provider."""
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "provider not found")
    db.query(ProviderKey).filter(ProviderKey.provider_id == p.id).delete()
    p.api_key_encrypted = ""
    p.api_key_mask = ""
    p.status = "untested"
    db.commit()
    _audit(db, admin, "provider_keys_deleted", provider_id=p.id, name=p.name)
    return _provider_out(p, db)


# --- key pool ----------------------------------------------------------------

class KeysBody(BaseModel):
    keys: str = ""
    label_prefix: str = ""


def _key_out(k: ProviderKey) -> dict:
    return {"id": k.id, "label": k.label, "api_key_mask": k.api_key_mask,
            "enabled": k.enabled, "status": k.status, "use_count": k.use_count,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "last_error": k.last_error}


@router.get("/providers/{provider_id}/keys")
def list_keys(provider_id: str, db: Session = Depends(get_db)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "provider not found")
    key_pool._rows(db, p)  # lazily migrate a legacy single key into the pool
    rows = (db.query(ProviderKey).filter(ProviderKey.provider_id == provider_id)
            .order_by(ProviderKey.created_at.asc()).all())
    return [_key_out(k) for k in rows]


@router.post("/providers/{provider_id}/keys")
def add_keys(provider_id: str, body: KeysBody, db: Session = Depends(get_db),
             admin: User = Depends(require_admin)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "provider not found")
    added = key_pool.add_keys(db, p, body.keys, body.label_prefix)
    _audit(db, admin, "provider_keys_added", provider_id=p.id, count=added)
    return {"added": added, "provider": _provider_out(p, db)}


@router.post("/providers/{provider_id}/keys/{key_id}/toggle")
def toggle_key(provider_id: str, key_id: str, db: Session = Depends(get_db)):
    k = db.get(ProviderKey, key_id)
    if not k or k.provider_id != provider_id:
        raise HTTPException(404, "key not found")
    k.enabled = not k.enabled
    db.commit()
    return _key_out(k)


@router.delete("/providers/{provider_id}/keys/{key_id}")
def delete_key(provider_id: str, key_id: str, db: Session = Depends(get_db),
               admin: User = Depends(require_admin)):
    k = db.get(ProviderKey, key_id)
    if not k or k.provider_id != provider_id:
        raise HTTPException(404, "key not found")
    db.delete(k)
    db.commit()
    _audit(db, admin, "provider_key_deleted", provider_id=provider_id, key_id=key_id)
    return {"deleted": key_id}


@router.post("/providers/{provider_id}/sync-models")
def sync_provider_models(provider_id: str, db: Session = Depends(get_db),
                         admin: User = Depends(require_admin)):
    """Reconcile the model registry with the provider's live catalog (prices,
    deprecations, context windows). Currently supported for Groq."""
    from ..services.model_catalog import sync_provider_models as run_sync
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "provider not found")
    try:
        summary = run_sync(db, p)
    except RuntimeError as e:
        raise HTTPException(400, redact_error(e)[:300]) from e
    _audit(db, admin, "provider_models_synced", provider_id=provider_id,
           summary={k: v for k, v in summary.items() if k != "provider"})
    return summary


@router.post("/providers/{provider_id}/test")
def test_provider(provider_id: str, db: Session = Depends(get_db)):
    p = db.get(Provider, provider_id)
    if not p:
        raise HTTPException(404, "provider not found")
    p.last_tested_at = datetime.now(UTC)
    if p.provider_type == "mock":
        p.status, p.last_error = "active", ""
        db.commit()
        return _provider_out(p, db)
    keys = key_pool.ordered_key_records(db, p, include_errored=True)
    if not keys:
        p.status, p.last_error = "error", "no API key configured"
        db.commit()
        return _provider_out(p, db)
    card = {"provider": p.provider_type, "base_url": p.base_url,
            "model_name": _test_model_for(db, p), "max_output_tokens": 16,
            "default_temperature": 0, "input_cost_per_1m": 0, "output_cost_per_1m": 0,
            "timeout_seconds": int(get_setting(db, "provider_call_timeout_seconds") or 20)}
    if p.provider_type == "openrouter":
        card["http_referer"] = str(get_setting(db, "openrouter_http_referer") or "").strip()
        card["app_title"] = str(get_setting(db, "openrouter_app_title") or "").strip()
    tested = []
    last_error = ""
    for record in keys:
        try:
            adapter = get_provider(card, record["plaintext"])
            adapter.complete("You are a health check.", "Reply with OK.", {})
            p.status, p.last_error = "active", ""
            key_pool.mark_ok(db, record["id"])
            db.commit()
            out = _provider_out(p, db)
            out["test"] = {"ok": True, "key_mask": record["mask"],
                           "model_name": card["model_name"],
                           "tested_keys": tested + [{"key_mask": record["mask"], "ok": True}]}
            return out
        except Exception as e:
            last_error = redact_error(e)[:300]
            tested.append({"key_mask": record["mask"], "ok": False, "error": last_error})
            if key_pool.is_permanent_key_error(last_error):
                key_pool.mark_error(db, record["id"], last_error)
            elif key_pool.is_transient_key_error(last_error):
                key_pool.mark_cooldown(db, record["id"], last_error, seconds=60)
    p.status = "error"
    p.last_error = last_error or "all keys failed"
    db.commit()
    out = _provider_out(p, db)
    out["test"] = {"ok": False, "model_name": card["model_name"], "tested_keys": tested}
    return out


def _test_model_for(db: Session, p: Provider) -> str:
    entry = (db.query(ModelEntry).filter(ModelEntry.provider_id == p.id,
                                         ModelEntry.enabled.is_(True))
             .order_by(ModelEntry.priority.asc()).first())
    return entry.model_name if entry else "gpt-4o-mini"


# --- model registry ----------------------------------------------------------

class ModelBody(BaseModel):
    display_name: str
    provider_id: str
    model_name: str
    enabled: bool = True
    cost_level: str = "medium"
    input_price_per_1m: float = 1
    output_price_per_1m: float = 2
    max_context_tokens: int = 128000
    max_output_tokens: int = 8000
    supports_tools: bool = True
    supports_json: bool = True
    supports_vision: bool = False
    supports_code: bool = True
    priority: int = 100
    notes: str = ""


def _model_out(m: ModelEntry) -> dict:
    return {c: getattr(m, c) for c in (
        "id", "display_name", "provider_id", "model_name", "enabled", "cost_level",
        "max_context_tokens", "max_output_tokens", "supports_tools", "supports_json",
        "supports_vision", "supports_code", "priority", "notes")} | {
        "input_price_per_1m": float(m.input_price_per_1m),
        "output_price_per_1m": float(m.output_price_per_1m)}


@router.get("/models")
def models(db: Session = Depends(get_db)):
    return [_model_out(m) for m in
            db.query(ModelEntry).order_by(ModelEntry.priority.asc()).all()]


@router.post("/models")
def create_model(body: ModelBody, db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    if not db.get(Provider, body.provider_id):
        raise HTTPException(400, "unknown provider_id")
    m = ModelEntry(**body.model_dump())
    db.add(m)
    db.commit()
    _audit(db, admin, "model_created", model_id=m.id, display_name=m.display_name,
           enabled=m.enabled)
    return _model_out(m)


@router.put("/models/{model_id}")
def update_model(model_id: str, body: ModelBody, db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    m = db.get(ModelEntry, model_id)
    if not m:
        raise HTTPException(404, "model not found")
    was_enabled = m.enabled
    for k, v in body.model_dump().items():
        setattr(m, k, v)
    db.commit()
    action = ("model_enabled" if m.enabled and not was_enabled else
              "model_disabled" if was_enabled and not m.enabled else "model_updated")
    _audit(db, admin, action, model_id=m.id, display_name=m.display_name, enabled=m.enabled)
    return _model_out(m)


@router.delete("/models/{model_id}")
def delete_model(model_id: str, db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    m = db.get(ModelEntry, model_id)
    if not m:
        raise HTTPException(404, "model not found")
    db.delete(m)
    db.commit()
    _audit(db, admin, "model_deleted", model_id=model_id)
    return {"deleted": True}


# --- tariffs -----------------------------------------------------------------

class TariffBody(BaseModel):
    name: str
    price_usd: float
    description: str = ""
    swarm_size: int = 4
    max_phases: int = 8
    model_budget_usd: float = 0
    compute_budget_usd: float = 0
    credit_grant: int = 0
    bonus_percent: int = 0
    enabled: bool = True
    allowed_project_modes: list[str] = []
    allowed_outputs: list[str] = []
    priority: int = 100


def _tariff_out(t: Tariff) -> dict:
    return {"id": t.id, "name": t.name, "price_usd": float(t.price_usd),
            "description": t.description, "swarm_size": t.swarm_size,
            "max_phases": t.max_phases,
            "model_budget_usd": float(t.model_budget_usd),
            "compute_budget_usd": float(t.compute_budget_usd),
            "credit_grant": t.credit_grant, "bonus_percent": t.bonus_percent,
            "enabled": t.enabled, "allowed_project_modes": t.allowed_project_modes,
            "allowed_outputs": t.allowed_outputs, "priority": t.priority}


@router.get("/tariffs")
def tariffs(db: Session = Depends(get_db)):
    return [_tariff_out(t) for t in db.query(Tariff).order_by(Tariff.price_usd.asc()).all()]


@router.post("/tariffs")
def create_tariff(body: TariffBody, db: Session = Depends(get_db),
                  admin: User = Depends(require_admin)):
    t = Tariff(**body.model_dump())
    db.add(t)
    db.commit()
    _audit(db, admin, "tariff_created", tariff_id=t.id, name=t.name, price_usd=float(t.price_usd))
    return _tariff_out(t)


@router.put("/tariffs/{tariff_id}")
def update_tariff(tariff_id: str, body: TariffBody, db: Session = Depends(get_db),
                  admin: User = Depends(require_admin)):
    t = db.get(Tariff, tariff_id)
    if not t:
        raise HTTPException(404, "tariff not found")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    db.commit()
    _audit(db, admin, "tariff_updated", tariff_id=t.id, name=t.name, price_usd=float(t.price_usd))
    return _tariff_out(t)


@router.delete("/tariffs/{tariff_id}")
def delete_tariff(tariff_id: str, db: Session = Depends(get_db)):
    t = db.get(Tariff, tariff_id)
    if not t:
        raise HTTPException(404, "tariff not found")
    db.delete(t)
    db.commit()
    return {"deleted": True}


# --- top-ups / billing -------------------------------------------------------

def _topup_out(row: CreditTopup) -> dict:
    return {
        "id": row.id,
        "user_id": row.user_id,
        "email": row.email,
        "credits": row.credits,
        "amount_usd": float(row.amount_usd),
        "provider": row.provider,
        "provider_ref": row.provider_ref,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "paid_at": row.paid_at.isoformat() if row.paid_at else None,
    }


@router.get("/topups")
def topups(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(CreditTopup).order_by(CreditTopup.created_at.desc())
    if status:
        q = q.filter(CreditTopup.status == status)
    return [_topup_out(r) for r in q.limit(200).all()]


@router.post("/topups/{topup_id}/approve")
def approve_topup(topup_id: str, body: dict, db: Session = Depends(get_db),
                  admin: User = Depends(require_admin)):
    row = db.get(CreditTopup, topup_id)
    if not row:
        raise HTTPException(404, "top-up not found")
    if row.status != "pending":
        raise HTTPException(409, "top-up already processed")
    user = db.get(User, row.user_id)
    if not user:
        raise HTTPException(404, "user not found")
    row.status = "paid"
    row.provider_ref = str(body.get("provider_ref") or "")
    row.paid_at = datetime.now(UTC)
    user.token_balance = (user.token_balance or 0) + row.credits
    user.lifetime_tokens_granted = (user.lifetime_tokens_granted or 0) + row.credits
    db.commit()
    _audit(db, admin, "topup_approved", topup_id=row.id, user_id=user.id,
           credits=row.credits, amount_usd=float(row.amount_usd))
    log_user_activity(db, user, "topup_credited",
                      meta={"topup_id": row.id, "credits": row.credits,
                            "amount_usd": float(row.amount_usd)})
    return _topup_out(row)


@router.post("/topups/{topup_id}/cancel")
def cancel_topup(topup_id: str, db: Session = Depends(get_db),
                 admin: User = Depends(require_admin)):
    row = db.get(CreditTopup, topup_id)
    if not row:
        raise HTTPException(404, "top-up not found")
    if row.status != "pending":
        raise HTTPException(409, "top-up already processed")
    row.status = "cancelled"
    db.commit()
    _audit(db, admin, "topup_cancelled", topup_id=row.id, user_id=row.user_id)
    return _topup_out(row)


# --- project types -----------------------------------------------------------

class ProjectTypeBody(BaseModel):
    key: str
    display_name: str
    description: str = ""
    enabled: bool = True
    requires_codebase: bool = True
    default_outputs: list[str] = []
    default_phases: list[str] = []
    recommended_budget_min: float = 20
    recommended_budget_max: float = 200
    template_prompt: str = ""
    notes: str = ""


def _ptype_out(t: ProjectType) -> dict:
    return {"id": t.id, "key": t.key, "display_name": t.display_name,
            "description": t.description, "enabled": t.enabled,
            "requires_codebase": t.requires_codebase,
            "default_outputs": t.default_outputs, "default_phases": t.default_phases,
            "recommended_budget_min": float(t.recommended_budget_min),
            "recommended_budget_max": float(t.recommended_budget_max),
            "template_prompt": t.template_prompt, "notes": t.notes}


@router.get("/project-types")
def project_types(db: Session = Depends(get_db)):
    return [_ptype_out(t) for t in db.query(ProjectType).order_by(ProjectType.key.asc()).all()]


@router.post("/project-types")
def create_project_type(body: ProjectTypeBody, db: Session = Depends(get_db)):
    if db.query(ProjectType).filter(ProjectType.key == body.key).first():
        raise HTTPException(409, "key already exists")
    t = ProjectType(**body.model_dump())
    db.add(t)
    db.commit()
    return _ptype_out(t)


@router.put("/project-types/{type_id}")
def update_project_type(type_id: str, body: ProjectTypeBody, db: Session = Depends(get_db)):
    t = db.get(ProjectType, type_id)
    if not t:
        raise HTTPException(404, "project type not found")
    for k, v in body.model_dump().items():
        setattr(t, k, v)
    db.commit()
    return _ptype_out(t)


# --- settings ----------------------------------------------------------------

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return all_settings(db)


@router.put("/settings")
def put_settings(body: dict, db: Session = Depends(get_db)):
    from ..services.settings_service import DEFAULTS
    for key, value in body.items():
        if key not in DEFAULTS:
            raise HTTPException(400, f"unknown setting: {key}")
        set_setting(db, key, value)
    return all_settings(db)


# --- logs --------------------------------------------------------------------

@router.get("/logs")
def logs(project_id: str | None = None, model_id: str | None = None,
         status: str | None = None, limit: int = 200, db: Session = Depends(get_db)):
    q = db.query(AgentCall).order_by(AgentCall.created_at.desc())
    if project_id:
        q = q.filter(AgentCall.project_id == project_id)
    if model_id:
        q = q.filter(AgentCall.model_id == model_id)
    if status:
        q = q.filter(AgentCall.status == status)
    limit = max(1, min(limit, 1000))
    return [{
        "project_id": c.project_id, "phase": c.phase_key, "model_id": c.model_id,
        "mandate": c.mandate, "cost_usd": float(c.cost_estimated_usd),
        "status": c.status,
        "provider_id": getattr(c, "provider_id", ""),
        "provider_type": getattr(c, "provider_type", ""),
        "provider_model_name": getattr(c, "provider_model_name", ""),
        "provider_key_mask": getattr(c, "provider_key_mask", ""),
        "error_message": getattr(c, "error_message", ""),
        "created_at": c.created_at.isoformat() if c.created_at else None,
    } for c in q.limit(limit).all()]


@router.get("/user-activity")
def user_activity(user_id: str | None = None, project_id: str | None = None,
                  action: str | None = None, limit: int = 200,
                  db: Session = Depends(get_db)):
    q = db.query(UserActivity).order_by(UserActivity.created_at.desc())
    if user_id:
        q = q.filter(UserActivity.user_id == user_id)
    if project_id:
        q = q.filter(UserActivity.project_id == project_id)
    if action:
        q = q.filter(UserActivity.action == action)
    limit = max(1, min(limit, 1000))
    return [{
        "id": r.id,
        "user_id": r.user_id,
        "email": r.email,
        "action": r.action,
        "project_id": r.project_id,
        "metadata": r.meta,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in q.limit(limit).all()]


@router.get("/projects/{project_id}/logs")
def project_logs(project_id: str, limit: int = 100, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    ws = workspace_path(project_id)
    limit = max(1, min(limit, 500))
    out: dict[str, list] = {}
    for name in ("events.jsonl", "agent-calls.jsonl", "command-runs.jsonl"):
        f = ws / "logs" / name
        out[name] = _tail_jsonl(f, limit)
    out["agent_calls_db"] = [
        {
            "phase": c.phase_key,
            "model_id": c.model_id,
            "mandate": c.mandate,
            "cost_usd": float(c.cost_estimated_usd),
            "status": c.status,
            "provider_id": getattr(c, "provider_id", ""),
            "provider_type": getattr(c, "provider_type", ""),
            "provider_model_name": getattr(c, "provider_model_name", ""),
            "provider_key_mask": getattr(c, "provider_key_mask", ""),
            "error_message": getattr(c, "error_message", ""),
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "output_preview": _preview_text(ws, c.output_path),
        }
        for c in (
            db.query(AgentCall)
            .filter(AgentCall.project_id == project_id)
            .order_by(AgentCall.created_at.desc())
            .limit(limit)
            .all()
        )
    ]
    out["summary"] = {
        "project_id": project.id,
        "status": project.status,
        "current_phase": project.current_phase,
        "events": len(out["events.jsonl"]),
        "agent_calls": len(out["agent_calls_db"]),
        "command_runs": len(out["command-runs.jsonl"]),
    }
    for row in out["command-runs.jsonl"]:
        if row.get("stdout_path"):
            row["stdout_preview"] = _preview_text(ws, row["stdout_path"], 900)
        if row.get("stderr_path"):
            row["stderr_preview"] = _preview_text(ws, row["stderr_path"], 900)
    return out
