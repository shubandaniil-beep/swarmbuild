"""Seed default providers, models, tariffs, project types, settings, admin user."""
import os
import secrets
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import settings as env
from ..lib.crypto import encrypt_key, mask_key
from ..lib.security import hash_password
from ..models import (
    ModelEntry,
    Project,
    ProjectPhase,
    ProjectType,
    Provider,
    SystemSetting,
    Tariff,
    User,
)
from . import key_pool
from .settings_service import DEFAULTS

_PROVIDERS = [
    ("Mock", "mock", "", ""),
    ("OpenAI", "openai", "https://api.openai.com/v1", env.OPENAI_API_KEY),
    ("Anthropic", "anthropic", "https://api.anthropic.com", env.ANTHROPIC_API_KEY),
    ("Gemini", "gemini", "https://generativelanguage.googleapis.com/v1beta/openai",
     env.GEMINI_API_KEY),
    ("DeepSeek", "deepseek", "https://api.deepseek.com/v1", env.DEEPSEEK_API_KEY),
    ("Qwen", "qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1", env.QWEN_API_KEY),
    ("Groq", "groq", "https://api.groq.com/openai/v1", env.GROQ_API_KEY),
    ("OpenRouter", "openrouter", "https://openrouter.ai/api/v1", env.OPENROUTER_API_KEY),
    ("GLM", "glm", env.GLM_BASE_URL, env.GLM_API_KEY),
]

_MODELS = [
    # (display, provider_type, model_name, cost_level, in$, out$, code)
    ("Mock Swarm v1", "mock", "mock-swarm-v1", "free", 0.01, 0.02, True),
    ("Mock Swarm Mini", "mock", "mock-swarm-mini", "free", 0.005, 0.01, True),
    ("GPT-5.5", "openai", "gpt-5.5", "high", 5, 30, True),
    ("Claude Opus 4.8", "anthropic", "claude-opus-4-8", "high", 5, 25, True),
    ("Claude Sonnet", "anthropic", "claude-sonnet-4-6", "medium", 3, 15, True),
    ("Gemini Pro", "gemini", "gemini-2.5-pro", "medium", 1.25, 10, True),
    ("Gemini Flash", "gemini", "gemini-2.5-flash", "low", 0.15, 0.6, True),
    ("DeepSeek Chat", "deepseek", "deepseek-chat", "low", 0.3, 1.2, True),
    ("DeepSeek Reasoner", "deepseek", "deepseek-reasoner", "medium", 0.55, 2.2, True),
    ("Qwen Coder", "qwen", "qwen3-coder", "medium", 1.6, 6.4, True),
    ("Groq Llama 3.3 70B", "groq", "llama-3.3-70b-versatile", "medium", 0.59, 0.79, True),
    ("Groq Llama 3.1 8B Instant", "groq", "llama-3.1-8b-instant", "low", 0.05, 0.08, True),
    ("Groq GPT OSS 120B", "groq", "openai/gpt-oss-120b", "medium", 0.15, 0.6, True),
    ("Groq GPT OSS 20B", "groq", "openai/gpt-oss-20b", "low", 0.075, 0.3, True),
    ("OpenRouter Cohere North Mini Code Free", "openrouter", "cohere/north-mini-code:free",
     "low", 0, 0, True),
    ("OpenRouter Poolside Laguna XS Free", "openrouter", "poolside/laguna-xs-2.1:free",
     "low", 0, 0, True),
    ("OpenRouter Qwen Coder Free", "openrouter", "qwen/qwen3-coder:free",
     "low", 0, 0, True),
    ("OpenRouter Nemotron Free", "openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free",
     "low", 0, 0, True),
    ("GLM 5.2", "glm", "glm-5.2", "high", 0.6, 2.2, True),
]

# (name, price_usd, swarm, max_phases, modes, credit_grant, bonus_%, description)
_TARIFFS = [
    ("Free Test Run", 1, 3, 5, ["code", "document", "business", "auto"], 100, 0,
     "Одна минимальная тестовая генерация: 100 credits = $1"),
    ("Fast Build", 20, 3, 5, ["code", "document", "auto"], 2000, 0,
     "Для простых code/document проектов"),
    ("Small MVP", 40, 4, 8, ["code", "document", "business", "auto"], 4400, 10,
     "Базовый pipeline (+10% бонус)"),
    ("Standard MVP", 100, 6, 9, ["code", "document", "business", "mixed", "auto"], 12000, 20,
     "Code + docs + business plan + pitch outline (+20% бонус)"),
    ("Heavy Build", 200, 8, 9, ["code", "document", "business", "mixed", "auto"], 26000, 30,
     "Полный pipeline + repair + audit (+30% бонус)"),
    ("Custom", 500, 8, 9, ["code", "document", "business", "mixed", "auto"], 70000, 40,
     "Крупные проекты (+40% бонус)"),
]

# (key, name, requires_codebase, default_outputs)
_PROJECT_TYPES = [
    ("auto", "Auto-detect", True, ["mvp", "docs"]),
    ("code_project", "Code project", True, ["mvp", "docs"]),
    ("document_project", "Document project", False, ["research_report", "docs"]),
    ("business_project", "Business project", False, ["business_plan", "pitch_outline"]),
    ("presentation_project", "Presentation", False, ["presentation_structure"]),
    ("research_project", "Research project", False, ["research_report"]),
    ("telegram_bot", "Telegram bot", True, ["mvp", "docs"]),
    ("mini_crm", "Mini CRM", True, ["mvp", "docs"]),
    ("landing_page", "Landing page", True, ["mvp", "docs"]),
    ("web_app", "Web app", True, ["mvp", "docs"]),
    ("dashboard", "Dashboard", True, ["mvp", "docs"]),
    ("integration", "Integration", True, ["mvp", "docs"]),
    ("automation_script", "Automation script", True, ["mvp", "docs"]),
    ("python_utility", "Python utility", True, ["mvp", "docs"]),
    ("saas_mvp", "SaaS MVP", True, ["mvp", "docs", "business_plan"]),
    ("mobile_app_concept", "Mobile app concept", False, ["technical_spec", "presentation_structure"]),
    ("education_project", "Education project", False, ["research_report", "docs"]),
    ("diploma_or_coursework", "Diploma / coursework", False, ["research_report", "presentation_structure"]),
    ("pitch_deck", "Pitch deck", False, ["pitch_outline", "presentation_structure"]),
    ("marketing_pack", "Marketing pack", False, ["marketing_plan", "branding_copy"]),
    ("custom", "Custom", True, ["mvp", "docs"]),
]


def seed_defaults(db: Session) -> None:
    if db.query(Provider).count() == 0:
        for name, ptype, base_url, key in _PROVIDERS:
            db.add(Provider(
                name=name, provider_type=ptype, base_url=base_url,
                api_key_encrypted=encrypt_key(key) if key else "",
                api_key_mask=mask_key(key) if key else "",
                enabled=True, status="active" if ptype == "mock" else "untested",
                priority=0 if ptype == "mock" else 100,
            ))
        db.commit()
    _sync_env_provider_keys(db)

    if db.query(ModelEntry).count() == 0:
        providers = {p.provider_type: p for p in db.query(Provider).all()}
        for display, ptype, model_name, cost, inp, outp, code in _MODELS:
            provider = providers.get(ptype)
            if not provider:
                continue
            db.add(ModelEntry(
                display_name=display, provider_id=provider.id, model_name=model_name,
                cost_level=cost, input_price_per_1m=inp, output_price_per_1m=outp,
                supports_code=code,
                priority=0 if ptype == "mock" else 100,
            ))
        db.commit()

    existing = {t.name: t for t in db.query(Tariff).all()}
    for name, price, swarm, max_phases, modes, credit_grant, bonus, desc in _TARIFFS:
        t = existing.get(name)
        if t is None:
            db.add(Tariff(
                name=name, price_usd=price, swarm_size=swarm, max_phases=max_phases,
                model_budget_usd=round(price * 0.5, 2),
                compute_budget_usd=round(price * 0.1, 2),
                credit_grant=credit_grant, bonus_percent=bonus,
                allowed_project_modes=modes, allowed_outputs=[], description=desc,
            ))
        else:
            # Keep default launch tariffs calibrated across local/staging DBs.
            t.price_usd = price
            t.swarm_size = swarm
            t.max_phases = max_phases
            t.model_budget_usd = round(price * 0.5, 2)
            t.compute_budget_usd = round(price * 0.1, 2)
            t.credit_grant = credit_grant
            t.bonus_percent = bonus
            t.allowed_project_modes = modes
            t.description = desc
        db.commit()

    if db.query(ProjectType).count() == 0:
        for key, name, requires_code, outputs in _PROJECT_TYPES:
            db.add(ProjectType(
                key=key, display_name=name, requires_codebase=requires_code,
                default_outputs=outputs, default_phases=[],
            ))
        db.commit()

    for key, value in DEFAULTS.items():
        if not db.get(SystemSetting, key):
            db.add(SystemSetting(key=key, value={"v": value}))
    db.commit()
    _ensure_runtime_model_defaults(db)
    _harden_runtime_settings(db)
    _recalibrate_legacy_credit_settings(db)
    _recover_transiently_errored_keys(db)

    admin_email = os.getenv("ADMIN_EMAIL") or os.getenv("FOUNDER_EMAIL") or "founder@swarmbuild.ai"
    if not db.query(User).filter(User.email == admin_email).first():
        db.add(User(email=admin_email, role="admin",
                    password_hash=hash_password(_founder_password())))
        db.commit()
    _disable_legacy_dev_admin(db, admin_email)
    _backfill_user_credits(db)
    from .pay_codes import backfill_pay_codes
    backfill_pay_codes(db)
    _mark_interrupted_projects(db)


def _sync_env_provider_keys(db: Session) -> None:
    """Import env keys into empty/new provider pools without overwriting UI keys."""
    by_type: dict[str, list[Provider]] = {}
    for provider in db.query(Provider).order_by(Provider.created_at.asc()).all():
        by_type.setdefault(provider.provider_type, []).append(provider)
    for name, ptype, base_url, key in _PROVIDERS:
        if ptype == "mock":
            continue
        candidates = by_type.get(ptype, [])
        provider = next(
            (p for p in candidates if p.name == name and p.base_url == base_url),
            candidates[0] if candidates else None,
        )
        if provider is None:
            provider = Provider(name=name, provider_type=ptype, base_url=base_url,
                                enabled=True, status="untested", priority=100)
            db.add(provider)
            db.commit()
            by_type.setdefault(ptype, []).append(provider)
        if key and key_pool.add_keys(db, provider, key, label_prefix="env-"):
            provider.status = "untested"
            db.commit()


def _founder_password() -> str:
    configured = os.getenv("ADMIN_PASSWORD") or os.getenv("FOUNDER_PASSWORD")
    if configured:
        return configured
    password_file = Path(__file__).resolve().parents[2] / ".founder-password"
    if password_file.exists():
        return password_file.read_text().strip()
    password = "sb-" + secrets.token_urlsafe(24)
    password_file.write_text(password)
    password_file.chmod(0o600)
    return password


def _recalibrate_legacy_credit_settings(db: Session) -> None:
    """Move pre-launch installs onto the 1 credit = $0.01 economy. Only rewrites
    the old mis-calibrated defaults (1000 / 5000); leaves any custom value alone."""
    from ..models import SystemSetting
    fixes = {
        "tokens_per_usd": ({1000}, 100),
        "demo_starting_credits": ({5000, 500}, 100),
    }
    for key, (legacy_values, new) in fixes.items():
        row = db.get(SystemSetting, key)
        if row and row.value.get("v") in legacy_values:
            row.value = {"v": new}
    db.commit()


def _ensure_runtime_model_defaults(db: Session) -> None:
    providers = {p.provider_type: p for p in db.query(Provider).all()}
    existing = {(m.provider_id, m.model_name) for m in db.query(ModelEntry).all()}
    changed = False
    for display, ptype, model_name, cost, inp, outp, code in _MODELS:
        provider = providers.get(ptype)
        if not provider or (provider.id, model_name) in existing:
            continue
        db.add(ModelEntry(
            display_name=display,
            provider_id=provider.id,
            model_name=model_name,
            cost_level=cost,
            input_price_per_1m=inp,
            output_price_per_1m=outp,
            supports_code=code,
            priority=999 if ptype == "mock" else 100,
            enabled=ptype != "mock",
        ))
        changed = True
    if changed:
        db.commit()


def _harden_runtime_settings(db: Session) -> None:
    """Keep old local DBs from silently routing production work to mock."""
    fixes = {
        "default_provider": ({"mock", "mock-swarm-v1"}, "auto"),
        "default_model": ({"mock", "mock-swarm-v1", "mock-swarm-mini"}, ""),
        "allow_mock_fallback": ({True, "true", "1"}, False),
        "provider_max_output_tokens": ({600}, 2000),
        # 20s starved free-tier models mid-generation → timeout → failover storm
        "provider_call_timeout_seconds": ({20}, 60),
    }
    changed = False
    for key, (legacy_values, new_value) in fixes.items():
        row = db.get(SystemSetting, key)
        if row and row.value.get("v") in legacy_values:
            row.value = {"v": new_value}
            changed = True
    mock_provider = db.query(Provider).filter(Provider.provider_type == "mock").first()
    if mock_provider and mock_provider.priority < 900:
        mock_provider.priority = 999
        changed = True
    for model in (db.query(ModelEntry).join(Provider, ModelEntry.provider_id == Provider.id)
                  .filter(Provider.provider_type == "mock").all()):
        if model.priority < 900:
            model.priority = 999
            changed = True
    groq = db.query(Provider).filter(Provider.provider_type == "groq").first()
    if groq and groq.priority > 20:
        groq.priority = 10
        changed = True
    if groq:
        for model in db.query(ModelEntry).filter(ModelEntry.provider_id == groq.id).all():
            if model.priority > 50:
                model.priority = 20
                changed = True
    if changed:
        db.commit()


def _recover_transiently_errored_keys(db: Session) -> None:
    """Older builds marked keys status=error on 429/quota, taking them out of
    rotation forever. Those errors heal with time — put such keys back into the
    pool so a one-minute rate limit can't permanently disable a provider."""
    from ..models import ProviderKey
    from .key_pool import is_permanent_key_error, is_transient_key_error

    changed = False
    for pk in db.query(ProviderKey).filter(ProviderKey.status == "error").all():
        err = pk.last_error or ""
        if is_transient_key_error(err) and not is_permanent_key_error(err):
            pk.status = "untested"
            pk.cooldown_until = None
            changed = True
    if changed:
        db.commit()


def _disable_legacy_dev_admin(db: Session, active_admin_email: str) -> None:
    if active_admin_email == "admin@swarmbuild.ai":
        return
    legacy = db.query(User).filter(User.email == "admin@swarmbuild.ai").first()
    if legacy and legacy.role == "admin":
        legacy.role = "user"
        legacy.disabled = True
        db.commit()


def _backfill_user_credits(db: Session) -> None:
    changed = False
    for user in db.query(User).all():
        if user.token_balance is None:
            user.token_balance = 100
            changed = True
        if user.lifetime_tokens_granted is None:
            user.lifetime_tokens_granted = 100
            changed = True
        if (user.role != "admin" and (user.lifetime_tokens_spent or 0) == 0
                and (user.token_balance or 0) in {500, 5000}
                and (user.lifetime_tokens_granted or 0) in {500, 5000}):
            user.token_balance = 100
            user.lifetime_tokens_granted = 100
            changed = True
        if user.email == "demo@swarmbuild.ai" and (user.token_balance or 0) > 100:
            spent = user.lifetime_tokens_spent or 0
            user.token_balance = 100
            user.lifetime_tokens_granted = max(user.lifetime_tokens_granted or 0, spent + 100)
            user.demo_generations_remaining = 1
            changed = True
        if user.lifetime_tokens_spent is None:
            user.lifetime_tokens_spent = 0
            changed = True
        if user.demo_generations_remaining is None:
            user.demo_generations_remaining = 1
            changed = True
    if changed:
        db.commit()


_MAX_AUTO_RESUMES = 3
# A project that produced activity newer than this is treated as still alive —
# a live worker (this process, or another on a multi-worker deploy) is on it, so
# re-queuing it would run its phases twice. Only projects silent past this window
# are considered orphaned by a restart.
_RESUME_STALE_SECONDS = 180


def _seconds_since(dt) -> float:
    """Age in seconds of a possibly-naive timestamp, treated as UTC."""
    from datetime import UTC, datetime
    if dt is None:
        return float("inf")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (datetime.now(UTC) - dt).total_seconds()


def _mark_interrupted_projects(db: Session) -> None:
    """After a backend restart, in-memory worker threads are gone. A restart is
    an infrastructure event, never a client-facing failure: interrupted projects
    are re-queued and resume from their last unfinished phase (done phases are
    skipped by the orchestrator). Only a project that keeps dying across
    several restarts is parked as failed — a crash loop must not burn budget
    forever."""
    from ..models import Event
    from .event_log import log_event
    from .project_intake import workspace_path

    interrupted = (db.query(Project)
                   .filter(Project.deleted.is_(False),
                           Project.status.in_(("queued", "running", "packaging", "repairing")))
                   .all())
    if not interrupted:
        return
    from ..workers.project_worker import enqueue, is_running

    for project in interrupted:
        previous = project.status
        current_phase = project.current_phase

        # Liveness guard — never re-queue a project that is still being worked
        # on, or the orchestrator runs its phases twice (duplicate issues, wasted
        # model spend). (1) this process is actively running it; (2) it produced
        # activity within the freshness window, so a live worker (here or on
        # another process in a multi-worker deploy) is probably still on it.
        if is_running(project.id):
            continue
        last_event = (db.query(Event.created_at)
                      .filter(Event.project_id == project.id)
                      .order_by(Event.created_at.desc()).first())
        last_at = last_event[0] if last_event else project.created_at
        if _seconds_since(last_at) < _RESUME_STALE_SECONDS:
            continue

        resumes = (db.query(Event)
                   .filter(Event.project_id == project.id,
                           Event.event_type == "worker_resumed").count())
        # unfinished phases go back to pending so the orchestrator re-runs them
        for phase in (db.query(ProjectPhase)
                      .filter(ProjectPhase.project_id == project.id,
                              ProjectPhase.status.in_(("queued", "running")))
                      .all()):
            phase.status = "pending"

        if resumes >= _MAX_AUTO_RESUMES:
            project.status = "failed"
            project.current_phase = None
            project.not_released_reason = "internal: worker interrupted repeatedly"
            db.commit()
            try:
                log_event(db, project.id, "worker_resume_exhausted",
                          f"Auto-resume limit reached ({_MAX_AUTO_RESUMES}); parked as failed",
                          {"previous_status": previous, "current_phase": current_phase},
                          workspace_path(project.id))
            except OSError:
                pass
            continue

        project.status = "queued"
        project.current_phase = None
        db.commit()
        try:
            log_event(db, project.id, "worker_resumed",
                      f"Worker interrupted by restart; auto-resuming from phase "
                      f"{current_phase or 'start'} (attempt {resumes + 1}/{_MAX_AUTO_RESUMES})",
                      {"previous_status": previous, "current_phase": current_phase},
                      workspace_path(project.id))
        except OSError:
            pass
        enqueue(project.id)
