"""Seed default providers, models, tariffs, project types, settings, admin user."""
import os
import secrets
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import settings as env
from ..lib.crypto import encrypt_key, mask_key
from ..lib.security import hash_password
from ..models import (ModelEntry, Project, ProjectPhase, ProjectType, Provider,
                      SystemSetting, Tariff, User)
from .settings_service import DEFAULTS

_PROVIDERS = [
    ("Mock", "mock", "", ""),
    ("OpenAI", "openai", "https://api.openai.com/v1", env.OPENAI_API_KEY),
    ("Anthropic", "anthropic", "https://api.anthropic.com", env.ANTHROPIC_API_KEY),
    ("Gemini", "gemini", "https://generativelanguage.googleapis.com/v1beta/openai",
     env.GEMINI_API_KEY),
    ("DeepSeek", "deepseek", "https://api.deepseek.com/v1", env.DEEPSEEK_API_KEY),
    ("Qwen", "qwen", "https://dashscope.aliyuncs.com/compatible-mode/v1", env.QWEN_API_KEY),
    ("OpenRouter", "openrouter", "https://openrouter.ai/api/v1", env.OPENROUTER_API_KEY),
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
    ("OpenRouter Cohere North Mini Code Free", "openrouter", "cohere/north-mini-code:free",
     "low", 0, 0, True),
    ("OpenRouter Poolside Laguna XS Free", "openrouter", "poolside/laguna-xs-2.1:free",
     "low", 0, 0, True),
    ("OpenRouter Qwen Coder Free", "openrouter", "qwen/qwen3-coder:free",
     "low", 0, 0, True),
    ("OpenRouter Nemotron Free", "openrouter", "nvidia/nemotron-3-ultra-550b-a55b:free",
     "low", 0, 0, True),
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

    admin_email = os.getenv("ADMIN_EMAIL") or os.getenv("FOUNDER_EMAIL") or "founder@swarmbuild.ai"
    if not db.query(User).filter(User.email == admin_email).first():
        db.add(User(email=admin_email, role="admin",
                    password_hash=hash_password(_founder_password())))
        db.commit()
    _disable_legacy_dev_admin(db, admin_email)
    _backfill_user_credits(db)
    _mark_interrupted_projects(db)


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
        "allow_mock_fallback": ({True, "true", "1", 1}, False),
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


def _mark_interrupted_projects(db: Session) -> None:
    """After a backend restart, in-memory worker threads are gone. Never leave
    projects looking live when there is no worker capable of completing them."""
    interrupted = (db.query(Project)
                   .filter(Project.deleted.is_(False),
                           Project.status.in_(("queued", "running", "packaging")))
                   .all())
    if not interrupted:
        return
    from .event_log import log_event
    from .project_intake import workspace_path

    for project in interrupted:
        previous = project.status
        current_phase = project.current_phase
        project.status = "failed"
        project.current_phase = None
        for phase in (db.query(ProjectPhase)
                      .filter(ProjectPhase.project_id == project.id,
                              ProjectPhase.status.in_(("queued", "running")))
                      .all()):
            phase.status = "failed"
        db.commit()
        try:
            log_event(db, project.id, "worker_interrupted",
                      "Backend restarted before the worker finished; restart the project to resume.",
                      {"previous_status": previous, "current_phase": current_phase},
                      workspace_path(project.id))
        except OSError:
            pass
