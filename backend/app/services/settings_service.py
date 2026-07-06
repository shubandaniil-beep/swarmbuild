"""System settings stored in DB; env is only the initial seed / fallback."""
import os

from sqlalchemy.orm import Session

from ..config import settings as env
from ..models import SystemSetting

DEFAULTS: dict[str, object] = {
    "default_provider": "auto" if env.DEFAULT_MODEL_PROVIDER == "mock" else env.DEFAULT_MODEL_PROVIDER,
    "default_model": "",
    "enable_mock_mode": True,
    "allow_mock_fallback": False,
    # swarm: tariff-sized rotating pool; single_agent: one selected model card
    # walks every phase sequentially. This is a runtime switch, not a schema
    # migration, so existing projects and tariffs keep their planned size.
    "execution_mode": "swarm",
    # Seeded from env: false → offline mock swarm out of the box; true → real
    # providers (needs at least one usable API key). Runtime switch lives in
    # the admin settings, env only sets the initial value.
    "enable_real_model_calls": env.ENABLE_REAL_MODEL_CALLS,
    "max_project_runtime_minutes": env.MAX_PROJECT_RUNTIME_MINUTES,
    "max_phase_runtime_minutes": env.MAX_PHASE_RUNTIME_MINUTES,
    "platform_fee_percent": env.PLATFORM_FEE_PERCENT,
    "tokens_per_usd": 100,          # 1 credit = $0.01 of user-facing budget
    "demo_starting_credits": 100,   # $1 starter balance for one tiny trial run
    "telegram_payment_bot_url": os.getenv("TELEGRAM_PAYMENT_BOT_URL", ""),
    "default_currency": "USD",
    "maintenance_mode": False,
    "public_registration_enabled": True,
    "max_accounts_per_fingerprint": 1,
    "max_accounts_per_ip_per_day": 3,
    "store_internal_prompts": False,
    "provider_call_timeout_seconds": 60,
    "provider_max_output_tokens": 8000,
    # rate-limit resilience: passes over the key pool per call, and the max
    # single wait while every key of a provider is cooling down
    "provider_retry_attempts": 3,
    "provider_retry_max_wait_seconds": 70,
    "parallel_agent_calls": True,
    "max_parallel_agent_calls": 4,
    "max_login_attempts": 8,
    "login_window_minutes": 15,
    "trust_proxy_headers": False,
    "allow_private_provider_urls": False,
    "allow_insecure_provider_urls": False,
    "openrouter_http_referer": os.getenv("OPENROUTER_HTTP_REFERER", "https://swarmbuild.ai"),
    "openrouter_app_title": os.getenv("OPENROUTER_APP_TITLE", "SwarmBuild AI"),
    # abuse / resource limits
    "max_agent_calls_per_project": 200,
    "max_repair_loops": 3,
    "max_output_chars": 200_000,      # per agent output, truncated beyond this
    "max_artifact_bytes": 5_000_000,  # per shippable file
    "max_brief_chars": 20_000,
    "block_download_on_secret_leak": False,  # redact by default; block if turned on
}


def get_setting(db: Session, key: str):
    row = db.get(SystemSetting, key)
    return row.value.get("v") if row else DEFAULTS.get(key)


def set_setting(db: Session, key: str, value) -> None:
    row = db.get(SystemSetting, key)
    if row:
        row.value = {"v": value}
    else:
        db.add(SystemSetting(key=key, value={"v": value}))
    db.commit()


def all_settings(db: Session) -> dict:
    out = dict(DEFAULTS)
    for row in db.query(SystemSetting).all():
        out[row.key] = row.value.get("v")
    return out
