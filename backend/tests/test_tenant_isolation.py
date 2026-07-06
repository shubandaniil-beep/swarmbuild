"""Tenant isolation: a regular user may only ever see their own projects.

Proves the fix for the cross-tenant leak: user1 must not reach user2's project
through ANY project endpoint (list/get/events/phases/artifacts/download/start/
continue/cancel), while an admin sees everything through the admin panel.

Identities are minted straight into the DB + signed tokens so the test is not
coupled to the registration/abuse-limit flow, and every request carries an
explicit bearer token against a clean (cookie-less) client.
"""
from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.lib.security import create_token
from app.main import app
from app.models import User


def _auth(email: str, role: str = "user") -> tuple[str, dict]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(email=email, role=role, password_hash="x",
                        token_balance=1_000_000, lifetime_tokens_granted=1_000_000,
                        lifetime_tokens_spent=0, demo_generations_remaining=1)
            db.add(user)
            db.commit()
        if user.role != role:
            user.role = role
            db.commit()
        return user.id, {"Authorization": f"Bearer {create_token(user.id, user.token_version or 0)}"}
    finally:
        db.close()


def _new_client() -> TestClient:
    # Bare client (own cookie jar); the session-scoped `client` fixture already
    # ran app startup/seed, so the shared DB is ready.
    return TestClient(app)


def _create_project(c: TestClient, headers: dict, title: str) -> str:
    res = c.post("/api/projects", headers=headers, json={
        "title": title, "brief": "Изолированный проект для проверки доступа.",
        "budget_usd": 1, "requested_outputs": ["mvp", "docs"],
    })
    assert res.status_code == 200, res.text
    return res.json()["project_id"]


def test_user_cannot_reach_another_users_project(client):
    c = _new_client()
    _, h1 = _auth("iso-user1@example.com")
    _, h2 = _auth("iso-user2@example.com")

    pid = _create_project(c, h1, "User1 secret project")

    # owner can see it
    assert c.get(f"/api/projects/{pid}", headers=h1).status_code == 200

    # every user-facing project endpoint must hide it from user2 (404, no leak)
    reads = [
        c.get(f"/api/projects/{pid}", headers=h2),
        c.get(f"/api/projects/{pid}/events", headers=h2),
        c.get(f"/api/projects/{pid}/phases", headers=h2),
        c.get(f"/api/projects/{pid}/artifacts", headers=h2),
        c.get(f"/api/projects/{pid}/download", headers=h2),
        c.get(f"/api/projects/{pid}/artifacts/does-not-matter/content", headers=h2),
        c.get(f"/api/projects/{pid}/artifacts/does-not-matter/download", headers=h2),
    ]
    for r in reads:
        assert r.status_code == 404, (r.request.url, r.status_code, r.text)

    writes = [
        c.post(f"/api/projects/{pid}/start", headers=h2),
        c.post(f"/api/projects/{pid}/cancel", headers=h2),
        c.post(f"/api/projects/{pid}/continue", headers=h2,
               json={"action": "steal", "budget_usd": 1}),
    ]
    for r in writes:
        assert r.status_code == 404, (r.request.url, r.status_code, r.text)

    # user2's own list never contains user1's project
    lst = c.get("/api/projects", headers=h2).json()
    assert all(p["project_id"] != pid for p in lst)

    # ...and user1's list does contain it
    lst1 = c.get("/api/projects", headers=h1).json()
    assert any(p["project_id"] == pid for p in lst1)


def test_user_cannot_reach_another_users_real_artifact(client):
    """The wildcard-id checks above prove routing; this proves a REAL artifact
    id of user1 is equally invisible to user2 (server-side, not UI hiding)."""
    from app.database import SessionLocal
    from app.models import Artifact
    from app.services.project_intake import workspace_path

    c = _new_client()
    _, h1 = _auth("iso-artifact-owner@example.com")
    _, h2 = _auth("iso-artifact-intruder@example.com")
    pid = _create_project(c, h1, "Project with real artifact")

    db = SessionLocal()
    try:
        art = Artifact(project_id=pid, artifact_type="final",
                       path="artifacts/README.md", display_name="README.md")
        db.add(art)
        db.commit()
        art_id = art.id
    finally:
        db.close()
    ws = workspace_path(pid)
    (ws / "artifacts").mkdir(parents=True, exist_ok=True)
    (ws / "artifacts" / "README.md").write_text("# secret readme\n")

    assert c.get(f"/api/projects/{pid}/artifacts/{art_id}/content",
                 headers=h2).status_code == 404
    assert c.get(f"/api/projects/{pid}/artifacts/{art_id}/download",
                 headers=h2).status_code == 404
    # …and the artifact listing of the intruder's own view stays empty
    assert c.get(f"/api/projects/{pid}/artifacts", headers=h2).status_code == 404


def test_admin_sees_all_projects_and_integrity(client):
    c = _new_client()
    _, hu = _auth("iso-user3@example.com")
    _, ha = _auth("founder@example.com", role="admin")

    pid = _create_project(c, hu, "User3 project visible to admin")

    admin_list = c.get("/api/admin/projects", headers=ha)
    assert admin_list.status_code == 200
    assert any(p["project_id"] == pid for p in admin_list.json())

    # admin-only integrity view is reachable for someone else's project
    integ = c.get(f"/api/admin/projects/{pid}/integrity", headers=ha)
    assert integ.status_code == 200
    assert integ.json()["project_id"] == pid

    # a regular user cannot reach the admin panel at all
    assert c.get("/api/admin/projects", headers=hu).status_code == 403
    assert c.get(f"/api/admin/projects/{pid}/integrity", headers=hu).status_code == 403
