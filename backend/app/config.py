import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is listed, this keeps old envs bootable.
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(PROJECT_DIR / ".env", override=False)
    load_dotenv(BASE_DIR / ".env", override=False)


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


class Settings:
    DATABASE_URL: str = _env("DATABASE_URL", f"sqlite:///{BASE_DIR / 'swarmbuild.db'}")
    STORAGE_PATH: Path = Path(_env("STORAGE_PATH", str(BASE_DIR / "data" / "projects")))

    OPENAI_API_KEY: str = _env("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: str = _env("ANTHROPIC_API_KEY")
    GEMINI_API_KEY: str = _env("GEMINI_API_KEY")
    DEEPSEEK_API_KEY: str = _env("DEEPSEEK_API_KEY")
    QWEN_API_KEY: str = _env("QWEN_API_KEY")
    GROQ_API_KEY: str = _env("GROQ_API_KEY")
    OPENROUTER_API_KEY: str = _env("OPENROUTER_API_KEY")

    OPENAI_BASE_URL: str = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ANTHROPIC_BASE_URL: str = _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    DEFAULT_MODEL_PROVIDER: str = _env("DEFAULT_MODEL_PROVIDER", "mock")
    ENABLE_REAL_MODEL_CALLS: bool = _bool("ENABLE_REAL_MODEL_CALLS")

    MAX_PROJECT_RUNTIME_MINUTES: int = int(_env("MAX_PROJECT_RUNTIME_MINUTES", "120"))
    MAX_PHASE_RUNTIME_MINUTES: int = int(_env("MAX_PHASE_RUNTIME_MINUTES", "30"))
    MAX_COMMAND_RUNTIME_SECONDS: int = int(_env("MAX_COMMAND_RUNTIME_SECONDS", "120"))

    PLATFORM_FEE_PERCENT: int = int(_env("PLATFORM_FEE_PERCENT", "30"))

    # Shared secret for the Telegram payment bot. The bot sends it as
    # `Authorization: Bearer <secret>` on /api/telegram/* calls (its SITE_API_KEY
    # must equal this). Empty ⇒ the /api/telegram integration is disabled.
    PAYMENT_BOT_SECRET: str = _env("PAYMENT_BOT_SECRET")


settings = Settings()
settings.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
