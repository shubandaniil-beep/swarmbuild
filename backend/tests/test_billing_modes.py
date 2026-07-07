import uuid

from app.database import SessionLocal
from app.lib.security import create_token
from app.models import CreditTopup, Project, ProjectPhase, User
from app.services.token_ledger import charge_phase_credits, refund_project_credits


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


def test_between_tariff_budget_is_not_undercharged_to_cheaper_package():
    """A budget that falls between tariff prices must cost at least the
    proportional base rate, never round DOWN to a cheaper package's grant
    (regression: a default $5 project was billed as the $1 Trial = 100 credits).
    Exact tariff prices still keep their bonus grant."""
    from app.services.credit_pricing import quote_credits_for_budget, tokens_per_usd
    db = SessionLocal()
    try:
        per_usd = tokens_per_usd(db)  # base rate, default 100 credits = $1
        # between-tariff budgets: proportional, not the $1 package
        for budget in (5, 10, 19, 25, 99):
            assert quote_credits_for_budget(db, budget) >= round(budget * per_usd)
        # exact tariff selections still grant their (bonus) package credits
        from app.models import Tariff
        for t in db.query(Tariff).filter(Tariff.enabled.is_(True)).all():
            q = quote_credits_for_budget(db, float(t.price_usd))
            assert q >= int(t.credit_grant)
    finally:
        db.close()


def test_refund_makes_client_whole_when_result_not_delivered(client):
    """A client charged per phase must be refunded when the project ends
    undownloadable (blocked/partial/internal-repair). Admin/bypass projects were
    never charged, so refund is a no-op. Refund is idempotent."""
    db = SessionLocal()
    try:
        user = User(email=f"refund-{uuid.uuid4()}@example.com", role="user",
                    password_hash="x", token_balance=900, lifetime_tokens_granted=1000,
                    lifetime_tokens_spent=100, demo_generations_remaining=0)
        db.add(user)
        db.flush()
        p = Project(title="Undelivered", brief="brief", budget_usd=1,
                    requested_outputs=[], user_id=user.id, status="failed",
                    release_decision="blocked", credits_estimate=100,
                    credits_spent=100, billing_mode="client")
        db.add(p)
        db.flush()
        db.add(ProjectPhase(project_id=p.id, phase_key="build_sprint",
                            credits_charged=100, budget_limit_usd=1, status="done"))
        db.commit()

        out = refund_project_credits(db, p, "not delivered: blocked")
        db.refresh(user)
        db.refresh(p)
        assert out["refunded"] == 100
        assert user.token_balance == 1000            # 900 + 100 back
        assert user.lifetime_tokens_spent == 0       # 100 - 100
        assert p.credits_spent == 0
        assert all(ph.credits_charged == 0 for ph in
                   db.query(ProjectPhase).filter(ProjectPhase.project_id == p.id))
        # idempotent: nothing left to refund
        assert refund_project_credits(db, p, "again")["refunded"] == 0
    finally:
        db.close()


def test_admin_topup_approval_is_single_use_and_input_bounded(client):
    from fastapi.testclient import TestClient

    from app.main import app

    db = SessionLocal()
    try:
        user = User(email=f"topup-target-{uuid.uuid4()}@example.com", role="user",
                    password_hash="x", token_balance=0, lifetime_tokens_granted=0,
                    lifetime_tokens_spent=0)
        admin = db.query(User).filter(User.email == "founder@example.com").first()
        db.add(user)
        db.flush()
        user_id = user.id
        topup = CreditTopup(user_id=user.id, email=user.email, credits=1000,
                            amount_usd=10, provider="telegram_stars",
                            status="pending")
        too_long_ref = CreditTopup(user_id=user.id, email=user.email, credits=1000,
                                   amount_usd=10, provider="telegram_stars",
                                   status="pending")
        db.add_all([topup, too_long_ref])
        db.commit()
        topup_id = topup.id
        too_long_ref_id = too_long_ref.id
        headers = {"Authorization": f"Bearer {create_token(admin.id, admin.token_version or 0)}"}
    finally:
        db.close()

    with TestClient(app) as admin_client:
        first = admin_client.post(f"/api/admin/topups/{topup_id}/approve",
                                  json={"provider_ref": "stars-ok-1"}, headers=headers)
        second = admin_client.post(f"/api/admin/topups/{topup_id}/approve",
                                   json={"provider_ref": "stars-ok-2"}, headers=headers)
        too_long = admin_client.post(f"/api/admin/topups/{too_long_ref_id}/approve",
                                     json={"provider_ref": "x" * 201}, headers=headers)

    assert first.status_code == 200, first.text
    assert second.status_code == 409, second.text
    assert too_long.status_code == 422, too_long.text

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        assert user.token_balance == 1000
        assert user.lifetime_tokens_granted == 1000
        assert db.get(CreditTopup, topup_id).provider_ref == "stars-ok-1"
        assert db.get(CreditTopup, too_long_ref_id).status == "pending"
    finally:
        db.close()
