import uuid

from app.database import SessionLocal
from app.lib.security import create_token
from app.models import Project, ProjectPhase, User
from app.services.token_ledger import charge_phase_credits


def _admin_project(mode: str, balance: int = 1_000) -> tuple[str, str]:
    db = SessionLocal()
    try:
        user = User(email=f"{mode}-{uuid.uuid4()}@example.com", role="admin", password_hash="x",
                    token_balance=balance, lifetime_tokens_granted=balance,
                    lifetime_tokens_spent=0, demo_generations_remaining=1)
        db.add(user)
        db.flush()
        project = Project(title=f"{mode} project", brief="brief", budget_usd=1,
                          requested_outputs=["mvp"], user_id=user.id,
                          credits_estimate=100, billing_mode=mode)
        db.add(project)
        db.flush()
        db.add(ProjectPhase(project_id=project.id, phase_key="intake"))
        db.commit()
        return user.id, project.id
    finally:
        db.close()


def test_admin_bypass_zero_charge_is_explicit(client):
    uid, pid = _admin_project("admin_bypass")

    db = SessionLocal()
    try:
        project = db.get(Project, pid)
        charge = charge_phase_credits(db, project, "intake")
        user = db.get(User, uid)
        assert charge["charged"] == 0
        assert charge["billing_mode"] == "admin_bypass"
        assert charge["billing_reason"] == "admin_bypass"
        assert user.token_balance == 1_000
        assert project.credits_spent == 0
    finally:
        db.close()


def test_admin_client_simulation_charges_like_client(client):
    uid, pid = _admin_project("client_simulation")

    db = SessionLocal()
    try:
        project = db.get(Project, pid)
        charge = charge_phase_credits(db, project, "intake")
        user = db.get(User, uid)
        assert charge["charged"] > 0
        assert charge["billing_mode"] == "client_simulation"
        assert charge["billing_reason"] == "client_credits_charged"
        assert user.token_balance == 1_000 - charge["charged"]
        assert project.credits_spent == charge["charged"]
    finally:
        db.close()


def test_dashboard_flags_released_client_zero_credit_as_billing_error(client):
    from fastapi.testclient import TestClient

    from app.main import app

    db = SessionLocal()
    try:
        user = User(email=f"zero-billing-{uuid.uuid4()}@example.com", role="user",
                    password_hash="x", token_balance=1_000,
                    lifetime_tokens_granted=1_000, lifetime_tokens_spent=0)
        db.add(user)
        admin = db.query(User).filter(User.email == "founder@example.com").first()
        db.flush()
        project = Project(title="Released zero credits", brief="brief", budget_usd=1,
                          requested_outputs=["mvp"], user_id=user.id,
                          status="ready", release_decision="release",
                          credits_estimate=100, credits_spent=0,
                          billing_mode="client")
        db.add(project)
        db.commit()
        headers = {"Authorization": f"Bearer {create_token(admin.id, admin.token_version or 0)}"}
    finally:
        db.close()

    with TestClient(app) as admin_client:
        res = admin_client.get("/api/admin/dashboard", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["released_zero_credit_projects"] >= 1
    assert body["zero_credit_status"] == "billing_error"
