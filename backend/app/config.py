import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'swarmbuild.db'}")
    STORAGE_PATH: Path = Path(os.getenv("STORAGE_PATH", str(BASE_DIR / "data" / "projects")))

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    ANTHROPIC_BASE_URL: str = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    DEFAULT_MODEL_PROVIDER: str = os.getenv("DEFAULT_MODEL_PROVIDER", "mock")
    ENABLE_REAL_MODEL_CALLS: bool = _bool("ENABLE_REAL_MODEL_CALLS")

    MAX_PROJECT_RUNTIME_MINUTES: int = int(os.getenv("MAX_PROJECT_RUNTIME_MINUTES", "120"))
    MAX_PHASE_RUNTIME_MINUTES: int = int(os.getenv("MAX_PHASE_RUNTIME_MINUTES", "30"))
    MAX_COMMAND_RUNTIME_SECONDS: int = int(os.getenv("MAX_COMMAND_RUNTIME_SECONDS", "120"))

    PLATFORM_FEE_PERCENT: int = int(os.getenv("PLATFORM_FEE_PERCENT", "30"))


settings = Settings()
settings.STORAGE_PATH.mkdir(parents=True, exist_ok=True)
