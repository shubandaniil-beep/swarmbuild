"""API smoke tests: health, auth guards, validation."""


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
