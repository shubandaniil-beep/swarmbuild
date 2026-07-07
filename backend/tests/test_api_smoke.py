"""API smoke tests: health, auth guards, validation."""

import time

from app.api.auth import _UNTRUSTED_FORWARDED_IP
from app.database import SessionLocal
from app.lib import rate_limit
from app.models import User
from app.services.settings_service import get_setting, set_setting


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_projects_require_auth(client):
    fresh = client
    fresh.cookies.clear()
    assert fresh.get("/api/projects").status_code == 401
    assert fresh.post("/api/projects", json={}).status_code == 401
    assert fresh.get("/api/admin/dashboard").status_code == 401


def test_admin_routes_forbidden_for_users(user_client):
    assert user_client.get("/api/admin/dashboard").status_code == 403
    assert user_client.get("/api/admin/providers").status_code == 403


def test_project_validation(user_client):
    res = user_client.post("/api/projects", json={
        "title": "", "brief": "", "budget_usd": -5,
    })
    assert res.status_code == 422


def test_project_requested_outputs_payload_is_bounded(user_client):
    too_many = user_client.post("/api/projects", json={
        "title": "Too many outputs",
        "brief": "brief",
        "budget_usd": 1,
        "requested_outputs": [f"out_{i}" for i in range(21)],
    })
    assert too_many.status_code == 422

    too_long = user_client.post("/api/projects", json={
        "title": "Long output",
        "brief": "brief",
        "budget_usd": 1,
        "requested_outputs": ["x" * 81],
    })
    assert too_long.status_code == 422


def test_login_rejects_bad_password(client):
    res = client.post("/api/auth/login", json={
        "email": "user@example.com", "password": "wrong-password-123",
    })
    assert res.status_code == 401


def test_me_returns_credit_fields(user_client):
    res = user_client.get("/api/auth/me")
    assert res.status_code == 200
    body = res.json()
    assert body["email"] == "user@example.com"
    assert body["token_balance"] > 0
    assert body["credits_per_usd"] > 0


def test_session_cookie_secure_flag_honors_forwarded_proto():
    """Behind a TLS-terminating proxy the app sees http; the Secure flag on the
    session cookie must still be set when X-Forwarded-Proto says https, or the
    cookie could leak over a downgraded request."""
    from types import SimpleNamespace

    from app.api.auth import _is_https

    def req(scheme, xfp=None):
        headers = {"x-forwarded-proto": xfp} if xfp else {}
        return SimpleNamespace(url=SimpleNamespace(scheme=scheme), headers=headers)

    assert _is_https(req("https")) is True
    assert _is_https(req("http", "https")) is True          # behind a TLS proxy
    assert _is_https(req("http", "https, http")) is True     # proxy chain
    assert _is_https(req("http")) is False                   # plain dev http
    assert _is_https(req("http", "http")) is False


def test_login_ip_limit_cannot_be_bypassed_with_x_forwarded_for(client):
    """Untrusted X-Forwarded-For values must not create fresh IP buckets."""
    rate_limit.clear("login", f"ip:{_UNTRUSTED_FORWARDED_IP}")
    stamp = time.time_ns()

    statuses = []
    for i in range(9):
        res = client.post("/api/auth/login", json={
            "email": f"xff-bypass-{stamp}-{i}@example.com",
            "password": "wrong-password-123",
        }, headers={"X-Forwarded-For": f"203.0.113.{i + 1}"})
        statuses.append(res.status_code)

    assert statuses[:8] == [401] * 8
    assert statuses[8] == 429


def test_registration_ip_limit_cannot_be_bypassed_with_x_forwarded_for(client):
    """Mass signup cannot rotate spoofed X-Forwarded-For to evade IP/day caps."""
    db = SessionLocal()
    old_limit = None
    try:
        old_limit = get_setting(db, "max_accounts_per_ip_per_day")
        existing = db.query(User).filter(User.signup_ip == _UNTRUSTED_FORWARDED_IP).count()
        set_setting(db, "max_accounts_per_ip_per_day", existing + 3)
    finally:
        db.close()

    stamp = time.time_ns()
    try:
        statuses = []
        for i in range(4):
            res = client.post("/api/auth/register", json={
                "email": f"xff-register-{stamp}-{i}@example.com",
                "password": "correct-password-123",
                "fingerprint": f"xff-register-{stamp}-{i}",
            }, headers={"X-Forwarded-For": f"198.51.100.{i + 1}"})
            statuses.append(res.status_code)

        assert statuses[:3] == [200, 200, 200]
        assert statuses[3] == 429
    finally:
        db = SessionLocal()
        try:
            set_setting(db, "max_accounts_per_ip_per_day", old_limit)
        finally:
            db.close()
