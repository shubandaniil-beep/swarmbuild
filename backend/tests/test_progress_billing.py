"""Billing honesty: a build that produced nothing is never sold as finished.

Drives the real orchestrator with a provider stub that returns only prose (no
file contract), so the build phase parses zero files. The pipeline must then:
  * mark the build phase as made_progress == False and charge it 0 credits,
  * land the project in `needs_internal_repair` (not a client-facing "ready"),
  * refuse the archive to the paying client.
This is the anti-pattern the whole change exists to prevent.
"""
from app.database import SessionLocal
from app.lib.security import create_token
from app.models import Project, ProjectPhase, User
from app.providers.base import ProviderResult
from app.services import agent_runner, phase_orchestrator
from app.services.project_intake import create_project


class _ProseOnlyProvider:
    """Always returns substantive prose but never a FILE: contract, so the file
    extractor yields nothing — a builder that 'talked' but did not build."""

    def complete(self, system, user, context=None):
        text = ("Here is a detailed narrative description of what the project "
                "would contain, with lots of reasoning and no actual code files "
                "written anywhere in this response. " * 4)
        return ProviderResult(text=text, input_tokens=100, output_tokens=200, files={})


def _make_user(email: str) -> str:
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(email=email, role="user", password_hash="x",
                     token_balance=1_000_000, lifetime_tokens_granted=1_000_000,
                     lifetime_tokens_spent=0, demo_generations_remaining=1)
            db.add(u)
            db.commit()
        return u.id
    finally:
        db.close()


def test_build_with_no_files_is_unbilled_and_not_released(client, monkeypatch):
    monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": _ProseOnlyProvider())

    uid = _make_user("prose-only@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, "Prose-only build", "Нужен рабочий Python-скрипт.",
                                 1, ["mvp"], "code_project", "code", "non_technical",
                                 "", user_id=uid)
        pid = project.id
        db.commit()
    finally:
        db.close()

    run_db = SessionLocal()
    try:
        phase_orchestrator.run_project(run_db, pid)
    finally:
        run_db.close()

    db = SessionLocal()
    try:
        project = db.get(Project, pid)
        # Honest terminal status — never presented to the client as finished.
        assert project.status == "needs_internal_repair", project.status
        assert project.release_decision == "needs_internal_repair"
        assert project.not_released_reason

        build = (db.query(ProjectPhase)
                 .filter(ProjectPhase.project_id == pid,
                         ProjectPhase.phase_key == "build_sprint").first())
        assert build is not None
        assert build.made_progress is False
        assert (build.credits_charged or 0) == 0  # runtime/parser failure is not billed

        # phases after the failed build never ran (no packaging → no false "ready")
        later = (db.query(ProjectPhase)
                 .filter(ProjectPhase.project_id == pid,
                         ProjectPhase.phase_key == "packaging").first())
        assert later.status != "done"
    finally:
        db.close()


def test_no_progress_download_is_refused(client, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": _ProseOnlyProvider())
    uid = _make_user("prose-only2@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, "Prose build 2", "Нужен скрипт.", 1, ["mvp"],
                                 "code_project", "code", "non_technical", "", user_id=uid)
        pid = project.id
        db.commit()
    finally:
        db.close()

    run_db = SessionLocal()
    try:
        phase_orchestrator.run_project(run_db, pid)
    finally:
        run_db.close()

    c = TestClient(app)
    headers = {"Authorization": f"Bearer {create_token(uid, 0)}"}
    res = c.get(f"/api/projects/{pid}/download", headers=headers)
    assert res.status_code == 403
