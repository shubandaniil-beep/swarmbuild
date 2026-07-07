import uuid

import app.config as config_module
from app.database import SessionLocal
from app.models import CreditTopup, User
from app.services import pay_codes

SECRET = "bot-shared-secret-123"


def _auth():
    return {"Authorization": f"Bearer {SECRET}"}


def _user(balance: int = 100) -> tuple[str, str]:
    db = SessionLocal()
    try:
        user = User(email=f"pay-{uuid.uuid4()}@example.com", role="user",
                    password_hash="x", token_balance=balance,
                    lifetime_tokens_granted=balance, lifetime_tokens_spent=0,
                    demo_generations_remaining=1,
                    pay_code=pay_codes.generate_unique_code(db))
        db.add(user)
        db.commit()
        return user.pay_code, user.id
    finally:
        db.close()


def test_registration_assigns_unique_pay_code(client):
    res = client.post("/api/auth/register", json={
        "email": f"reg-{uuid.uuid4()}@example.com",
        "password": "reg-test-password-123",
    })
    assert res.status_code == 200, res.text
    code = res.json()["user"]["pay_code"]
    assert len(code) == 6 and code.isdigit()


def test_link_binds_telegram_id(client):
    code, uid = _user()
    db = SessionLocal()
    try:
        user = pay_codes.link_telegram(db, code=code, telegram_id="555")
        assert user.id == uid
        assert db.get(User, uid).telegram_id == "555"
    finally:
        db.close()


def test_link_rejects_unknown_code(client):
    db = SessionLocal()
    try:
        code = pay_codes.generate_unique_code(db)
        try:
            pay_codes.link_telegram(db, code=code, telegram_id="1")
            raise AssertionError("unknown code should raise")
        except pay_codes.InvalidLinkCode:
            pass
    finally:
        db.close()


def test_link_rejects_telegram_taken_by_other(client):
    code_a, _ = _user()
    code_b, _ = _user()
    db = SessionLocal()
    try:
        pay_codes.link_telegram(db, code=code_a, telegram_id="777")
        try:
            pay_codes.link_telegram(db, code=code_b, telegram_id="777")
            raise AssertionError("duplicate telegram id should raise")
        except pay_codes.InvalidLinkCode:
            pass
    finally:
        db.close()


def test_credit_by_telegram_and_idempotency(client):
    code, uid = _user(balance=100)
    db = SessionLocal()
    try:
        pay_codes.link_telegram(db, code=code, telegram_id="900")
        first = pay_codes.credit_by_telegram_id(
            db, telegram_id="900", credits=500, amount_usd=5, external_id="ch-1")
        assert first["status"] == "credited" and first["balance"] == 600
        dup = pay_codes.credit_by_telegram_id(
            db, telegram_id="900", credits=500, amount_usd=5, external_id="ch-1")
        assert dup["status"] == "duplicate"
        assert db.get(User, uid).token_balance == 600
        assert db.query(CreditTopup).filter(CreditTopup.provider_ref == "ch-1").count() == 1
    finally:
        db.close()


def test_credit_unlinked_raises(client):
    db = SessionLocal()
    try:
        try:
            pay_codes.credit_by_telegram_id(
                db, telegram_id="nolink", credits=10, amount_usd=1, external_id="x")
            raise AssertionError("should raise for unlinked id")
        except pay_codes.AccountNotLinked:
            pass
    finally:
        db.close()


# --- HTTP contract the bot actually calls ------------------------------------

def test_http_flow_link_credit_balance(client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "PAYMENT_BOT_SECRET", SECRET)
    code, uid = _user(balance=0)

    linked = client.post("/api/telegram/link", headers=_auth(),
                         json={"code": code, "telegram_id": 12345})
    assert linked.status_code == 200, linked.text
    assert linked.json()["success"] is True

    credited = client.post("/api/telegram/credit", headers=_auth(),
                          json={"telegram_id": 12345, "amount": 150,
                                "external_id": "tg_stars_abc"})
    assert credited.status_code == 200, credited.text
    assert credited.json() == {"success": True, "balance": 150}

    bal = client.get("/api/telegram/balance?telegram_id=12345", headers=_auth())
    assert bal.status_code == 200
    assert bal.json() == {"balance": 150}


def test_http_credit_unlinked_returns_404(client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "PAYMENT_BOT_SECRET", SECRET)
    res = client.post("/api/telegram/credit", headers=_auth(),
                      json={"telegram_id": 999999, "amount": 10, "external_id": "y"})
    assert res.status_code == 404


def test_http_bad_secret_rejected(client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "PAYMENT_BOT_SECRET", SECRET)
    res = client.post("/api/telegram/link",
                      headers={"Authorization": "Bearer wrong"},
                      json={"code": "123456", "telegram_id": 1})
    assert res.status_code == 401


def test_http_disabled_without_secret(client, monkeypatch):
    monkeypatch.setattr(config_module.settings, "PAYMENT_BOT_SECRET", "")
    res = client.get("/api/telegram/balance?telegram_id=1", headers=_auth())
    assert res.status_code == 503
