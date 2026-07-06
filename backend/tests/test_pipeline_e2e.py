"""End-to-end: register → estimate → create → run swarm (mock) → download zip.

The default test settings force the mock provider, so the whole pipeline runs
offline and deterministically.
"""
import io
import time
import zipfile

BRIEF = ("У меня автомойка. Нужен сайт, мини-CRM, Telegram-бот для записи "
         "клиентов и калькулятор стоимости услуг.")


def _wait_until_finished(client, project_id: str, timeout_s: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout_s
    last = {}
    while time.monotonic() < deadline:
        last = client.get(f"/api/projects/{project_id}").json()
        if last["status"] not in ("accepted", "queued", "running", "packaging"):
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
    assert project["status"] in ("ready", "partial_ready"), project

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
