"""Test fixtures: isolated sqlite DB + storage dir per test session.

Environment must be prepared before `app.config` is imported, so this file
sets it at collection time (pytest imports conftest before test modules).
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="swarmbuild-test-"))

os.environ["DATABASE_URL"] = f"sqlite:///{_TMP / 'test.db'}"
os.environ["STORAGE_PATH"] = str(_TMP / "projects")
os.environ["ENCRYPTION_SECRET"] = "test-secret-not-for-production"
os.environ["ADMIN_EMAIL"] = "founder@example.com"
os.environ["ADMIN_PASSWORD"] = "founder-test-password-123"
os.environ["ENABLE_REAL_MODEL_CALLS"] = "false"
os.environ["DEFAULT_MODEL_PROVIDER"] = "mock"
# Never let a developer's real .env leak keys into the test registry.
for _key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
             "DEEPSEEK_API_KEY", "QWEN_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
    os.environ[_key] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def user_client(client):
    """A client with a registered, logged-in regular user."""
    res = client.post("/api/auth/register", json={
        "email": "user@example.com",
        "password": "user-test-password-123",
    })
    assert res.status_code == 200, res.text
    return client
