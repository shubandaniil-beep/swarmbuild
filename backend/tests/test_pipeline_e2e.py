"""End-to-end: register → estimate → create → run swarm (mock) → download zip.

The default test settings force the mock provider, so the whole pipeline runs
offline and deterministically.
"""
import io
import json
import time
import zipfile

BRIEF = ("У меня автомойка. Нужен сайт, мини-CRM, Telegram-бот для записи "
         "клиентов и калькулятор стоимости услуг.")


def _wait_until_finished(client, project_id: str, timeout_s: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout_s
    last = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/projects/{project_id}").json()
        if last["status"] not in ("accepted", "queued", "running", "packaging", "repairing"):
            return last
        time.sleep(0.5)
    raise AssertionError(f"pipeline did not finish in time; last status: {last.get('status')}")


def test_full_mock_pipeline(user_client):
    est = user_client.post("/api/projects/estimate", json={"budget_usd": 1}).json()
    assert est["credits_estimate"] > 0

    res = user_client.post("/api/projects", json={
        "title": "Автомойка под ключ",
        "brief": BRIEF,
        "budget_usd": 1,
        "requested_outputs": ["mvp", "docs"],
    })
    assert res.status_code == 200, res.text
    project_id = res.json()["project_id"]

    res = user_client.post(f"/api/projects/{project_id}/start")
    assert res.status_code == 200, res.text

    project = _wait_until_finished(user_client, project_id)
    # The mock swarm writes a real, valid repo and passes the deterministic
    # gates, so an honest run reaches a released state.
    assert project["status"] == "ready", project
    assert project["release_decision"] == "release", project
    assert project["downloadable"] is True, project

    phases = user_client.get(f"/api/projects/{project_id}/phases").json()
    assert phases and all(p["status"] == "done" for p in phases)

    events = user_client.get(f"/api/projects/{project_id}/events").json()
    assert any(e["type"] == "packaged" for e in events)

    artifacts = user_client.get(f"/api/projects/{project_id}/artifacts").json()
    names = {a["display_name"] for a in artifacts}
    assert {"README.md", "limitations.md"} <= names

    res = user_client.get(f"/api/projects/{project_id}/download")
    assert res.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(res.content))
    assert any(name.endswith("README.md") for name in archive.namelist())


def test_fresh_user_full_pipeline_with_repair_charges_and_downloads(client):
    from fastapi.testclient import TestClient

    from app.database import SessionLocal
    from app.main import app
    from app.models import AgentCall, ProjectPhase, User
    from app.services.project_intake import workspace_path

    with TestClient(app) as c:
        email = f"client-e2e-{time.time_ns()}@example.com"
        res = c.post("/api/auth/register", json={
            "email": email,
            "password": "user-test-password-123",
        })
        assert res.status_code == 200, res.text
        user_id = res.json()["user"]["id"]

        db = SessionLocal()
        try:
            user = db.get(User, user_id)
            user.token_balance = 20_000
            user.lifetime_tokens_granted = 20_000
            user.demo_generations_remaining = 0
            db.commit()
        finally:
            db.close()

        start_balance = c.get("/api/auth/me").json()["token_balance"]
        res = c.post("/api/projects", json={
            "title": "Client full repair E2E",
            "brief": BRIEF,
            "budget_usd": 100,
            "requested_outputs": ["mvp", "docs"],
            "project_type": "code_project",
            "project_mode": "code",
        })
        assert res.status_code == 200, res.text
        project_id = res.json()["project_id"]
        assert res.json()["billing_mode"] == "client"
        assert res.json()["admin_bypass"] is False

        res = c.post(f"/api/projects/{project_id}/start")
        assert res.status_code == 200, res.text
        project = _wait_until_finished(c, project_id, timeout_s=120)

        assert project["status"] == "ready", project
        assert project["release_decision"] == "release", project
        assert project["downloadable"] is True
        assert project["billing_mode"] == "client"
        assert project["client_billing_enabled"] is True
        assert project["credits_spent"] > 0
        assert project["zero_credit_reason"] == "client_credits_charged"

        final_balance = c.get("/api/auth/me").json()["token_balance"]
        assert final_balance == start_balance - project["credits_spent"]

        ws = workspace_path(project_id)
        assert (ws / "repo").exists()
        assert any((ws / "repo").rglob("*.py"))
        release = json.loads((ws / "reviews" / "release-decision.json").read_text())
        assert release["decision"] == "release"
        assert release["gates"]
        assert not release.get("hard_failed")

        db = SessionLocal()
        try:
            calls = db.query(AgentCall).filter(AgentCall.project_id == project_id).all()
            phases = db.query(ProjectPhase).filter(ProjectPhase.project_id == project_id).all()
            assert calls
            assert any(p.phase_key == "repair_sprint" and p.status == "done" for p in phases)
            assert sum(p.credits_charged or 0 for p in phases) == project["credits_spent"]
        finally:
            db.close()

        res = c.get(f"/api/projects/{project_id}/download")
        assert res.status_code == 200, res.text
        archive = zipfile.ZipFile(io.BytesIO(res.content))
        names = set(archive.namelist())
        assert any(name.endswith("README.md") for name in names)
        assert any(name.endswith("INSTALL.md") for name in names)
        assert not any(name.startswith("reviews/") for name in names)


def test_download_requires_auth(client):
    fresh = client
    cookies = dict(fresh.cookies)
    fresh.cookies.clear()
    try:
        res = fresh.get("/api/projects/nonexistent/download")
        assert res.status_code == 401
    finally:
        for k, v in cookies.items():
            fresh.cookies.set(k, v)


def test_instant_magic_button_prompt_to_ready(client):
    """No-code flow: one prompt, one request — the platform picks the title,
    budget and type, starts the swarm itself, and the client only waits for a
    downloadable result."""
    from fastapi.testclient import TestClient

    from app.database import SessionLocal
    from app.lib.security import create_token
    from app.main import app
    from app.models import User

    with TestClient(app) as c:
        db = SessionLocal()
        try:
            u = User(email=f"magic-{time.time_ns()}@example.com", role="user",
                     password_hash="x", token_balance=100,
                     lifetime_tokens_granted=100, lifetime_tokens_spent=0,
                     demo_generations_remaining=1)
            db.add(u)
            db.commit()
            user_id = u.id
        finally:
            db.close()
        c.headers["Authorization"] = f"Bearer {create_token(user_id, 0)}"

        res = c.post("/api/projects/instant", json={"prompt": BRIEF})
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["status"] == "queued"          # started without extra clicks
        assert body["budget_usd"] > 0              # platform picked the package
        assert "автомойка" in body["title"].lower()

        project = _wait_until_finished(c, body["project_id"])
        assert project["status"] == "ready", project
        assert project["downloadable"] is True

        res = c.get(f"/api/projects/{body['project_id']}/download")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("application/zip")

        # the trial slot was consumed by the instant run
        db = SessionLocal()
        try:
            assert (db.get(User, user_id).demo_generations_remaining or 0) == 0
        finally:
            db.close()


def test_instant_refused_without_credits(client):
    from fastapi.testclient import TestClient

    from app.database import SessionLocal
    from app.lib.security import create_token
    from app.main import app
    from app.models import User

    with TestClient(app) as c:
        db = SessionLocal()
        try:
            u = User(email=f"magic-broke-{time.time_ns()}@example.com", role="user",
                     password_hash="x", token_balance=0,
                     lifetime_tokens_granted=0, lifetime_tokens_spent=0,
                     demo_generations_remaining=0)
            db.add(u)
            db.commit()
            user_id = u.id
        finally:
            db.close()
        c.headers["Authorization"] = f"Bearer {create_token(user_id, 0)}"
        res = c.post("/api/projects/instant", json={"prompt": BRIEF})
        assert res.status_code == 402
