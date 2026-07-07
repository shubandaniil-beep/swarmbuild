"""Release integrity: the paid client never receives an unfinished archive.

Covers the trust boundary end-to-end at the seams:
* progress proof — an LLM call is not progress; only files/artifacts/closed
  tasks are (spec §7.7);
* deterministic gates — broken code / missing deps fail and open issues (§7.9);
* download gate — only status=ready + release_decision=release is downloadable
  by a client; partial/draft is admin-only (§7.10).
"""
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import SessionLocal
from app.lib.security import create_token
from app.main import app
from app.models import Issue, Project, User
from app.services import build_integrity
from app.services.project_intake import create_project, workspace_path


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


# --------------------------------------------------------------------------- #
# progress proof                                                              #
# --------------------------------------------------------------------------- #

def test_llm_output_without_files_is_not_progress(tmp_path):
    ws = tmp_path
    (ws / "repo").mkdir()
    diff = build_integrity.diff_repo({}, {})  # nothing written
    proof = build_integrity.assess_phase_progress(
        ws, "build_sprint", repo_diff=diff,
        outputs={"builder": ["Sure! Here is a great plan with lots of prose."]},
        issues_before=0, issues_after=0, is_code_project=True)
    assert proof["made_progress"] is False
    assert "no parsed files" in proof["reason"]


def test_files_written_is_progress(tmp_path):
    ws = tmp_path
    (ws / "repo").mkdir()
    (ws / "repo" / "main.py").write_text("print('hi')\n")
    after = build_integrity.snapshot_repo(ws)
    diff = build_integrity.diff_repo({}, after)
    # progress is the builder's parsed file contract, not any file in repo/
    proof = build_integrity.assess_phase_progress(
        ws, "build_sprint", repo_diff=diff, outputs={"builder": ["log"]},
        issues_before=0, issues_after=0, is_code_project=True, parsed_files=1)
    assert proof["made_progress"] is True
    assert proof["signals"]["parsed_files"] == 1


def test_prose_log_in_repo_is_not_build_progress(tmp_path):
    """A build phase that only wrote a prose implementation-log into repo/ (which
    the orchestrator does routinely) but emitted no contract files is NOT progress."""
    ws = tmp_path
    (ws / "repo").mkdir()
    (ws / "repo" / "implementation-log.md").write_text("# lots of prose about the plan\n" * 5)
    after = build_integrity.snapshot_repo(ws)
    diff = build_integrity.diff_repo({}, after)
    proof = build_integrity.assess_phase_progress(
        ws, "build_sprint", repo_diff=diff, outputs={"lead": ["log"]},
        issues_before=0, issues_after=0, is_code_project=True, parsed_files=0)
    assert proof["made_progress"] is False


def test_repair_progress_requires_closed_or_changed(tmp_path):
    ws = tmp_path
    (ws / "repo").mkdir()
    diff = build_integrity.diff_repo({}, {})
    none = build_integrity.assess_phase_progress(
        ws, "repair_sprint", repo_diff=diff, outputs={"repairer": ["done"]},
        issues_before=3, issues_after=3, is_code_project=True)
    assert none["made_progress"] is False
    closed = build_integrity.assess_phase_progress(
        ws, "repair_sprint", repo_diff=diff, outputs={"repairer": ["done"]},
        issues_before=3, issues_after=1, is_code_project=True)
    assert closed["made_progress"] is True
    assert closed["signals"]["open_tasks_decreased"] == 2


# --------------------------------------------------------------------------- #
# deterministic gates                                                         #
# --------------------------------------------------------------------------- #

def _write_repo(ws: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = ws / "repo" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_gates_pass_on_valid_repo(tmp_path):
    _write_repo(tmp_path, {
        "main.py": "def main():\n    print('ok')\n\n\nif __name__ == '__main__':\n    main()\n",
        "requirements.txt": "requests>=2.0\n",
        "README.md": "# App\n\n```\npip install -r requirements.txt\npython main.py\n```\n",
    })
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "INSTALL.md").write_text("Run `pip install -r requirements.txt`\n")
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert result["passed"] is True, result["failed"]
    assert not result["hard_failed"]


def test_gates_fail_on_broken_python_and_open_issues(client, tmp_path):
    _write_repo(tmp_path, {
        "main.py": "def main(:\n  syntax error here\n",   # will not parse
        "requirements.txt": "!!!not a package!!!\n",
        "README.md": "# App runs python ghost.py\n",       # references missing file
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert result["passed"] is False
    assert "python_syntax_ok" in result["failed"]
    assert "dependencies_valid" in result["failed"]
    assert result["hard_failed"]  # blocks a full release

    # failed gates become tracked issues (idempotently)
    db = SessionLocal()
    try:
        proj = Project(user_id="ghost", title="broken", brief="b", budget_usd=1,
                       status="running")
        db.add(proj)
        db.commit()
        created = build_integrity.issues_from_gate_failures(db, proj.id, result)
        assert created >= 2
        again = build_integrity.issues_from_gate_failures(db, proj.id, result)
        assert again == 0  # no duplicates
        issues = db.query(Issue).filter(Issue.project_id == proj.id).all()
        assert any(i.title == "GATE-python_syntax_ok" and i.severity == "critical"
                   for i in issues)
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# download gate                                                               #
# --------------------------------------------------------------------------- #

def _make_partial_project(owner_id: str) -> str:
    db = SessionLocal()
    try:
        p = create_project(db, "Partial build", "brief", 1, ["mvp"], "auto", "auto",
                           "non_technical", "", user_id=owner_id)
        p.status = "partial_ready"
        p.release_decision = "partial_release"
        p.not_released_reason = "not released: build gate failed"
        db.commit()
        pid = p.id
    finally:
        db.close()
    ws = workspace_path(pid)
    (ws / "artifacts").mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ws / "artifacts" / "project.zip", "w") as zf:
        zf.writestr("README.md", "# partial\n")
    return pid


def test_client_cannot_download_partial_but_admin_can(client):
    c = TestClient(app)
    uid, hu = _auth("gate-owner@example.com")
    _, ha = _auth("founder@example.com", role="admin")
    pid = _make_partial_project(uid)

    # owner sees the project, but it is not downloadable
    view = c.get(f"/api/projects/{pid}", headers=hu)
    assert view.status_code == 200
    assert view.json()["downloadable"] is False

    # the paying client is refused the partial archive (403, not a silent 200)
    denied = c.get(f"/api/projects/{pid}/download", headers=hu)
    assert denied.status_code == 403
    body = denied.json()["detail"]
    assert body["status"] == "partial_ready"

    # the founder can still pull it for investigation
    allowed = c.get(f"/api/projects/{pid}/download", headers=ha)
    assert allowed.status_code == 200
    assert allowed.headers["content-type"].startswith("application/zip")


def test_released_project_is_downloadable(client):
    c = TestClient(app)
    uid, hu = _auth("gate-owner2@example.com")
    db = SessionLocal()
    try:
        p = create_project(db, "Released build", "brief", 1, ["mvp"], "auto", "auto",
                           "non_technical", "", user_id=uid)
        p.status = "ready"
        p.release_decision = "release"
        db.commit()
        pid = p.id
    finally:
        db.close()
    ws = workspace_path(pid)
    (ws / "artifacts").mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ws / "artifacts" / "project.zip", "w") as zf:
        zf.writestr("README.md", "# ready\n")

    res = c.get(f"/api/projects/{pid}/download", headers=hu)
    assert res.status_code == 200


# --------------------------------------------------------------------------- #
# review-issue severity — agents may not fabricate a release-blocking critical #
# --------------------------------------------------------------------------- #

def test_agent_review_critical_is_capped_to_major_and_does_not_block(client):
    """A reviewer that self-labels a hallucinated finding "critical" (e.g.
    "missing requirements.txt" on a valid stdlib-only project) must not
    hard-block a build whose deterministic gates all pass. Only GATE-* issues
    carry `critical`; agent findings cap at `major` (advisory, repair-eligible).
    """
    from app.services.phase_orchestrator import _collect_issues, _review_severity
    from app.services.release_policy import evaluate

    # pure helper: agent over-escalation is capped, real minor kept
    assert _review_severity("critical") == "major"
    assert _review_severity("blocker") == "major"
    assert _review_severity("major") == "major"
    assert _review_severity("minor") == "minor"
    assert _review_severity(None) == "minor"

    uid, _ = _auth("review-sev@example.com")
    db = SessionLocal()
    try:
        p = create_project(db, "Stdlib CLI", "A tiny stdlib-only Python CLI.", 1,
                           [], "auto", "auto", "non_technical", "", user_id=uid)
        pid = p.id

        review = "Findings:\n```json\n" + json.dumps([
            {"id": "ISSUE-001", "title": "Missing requirements.txt",
             "severity": "critical", "description": "no manifest",
             "suggested_fix": "add requirements.txt"},
        ]) + "\n```\n"
        _collect_issues(db, p, workspace_path(pid), [review])

        created = db.query(Issue).filter(Issue.project_id == pid).all()
        assert len(created) == 1
        assert created[0].severity == "major"  # not critical

        # a real deliverable tree with all doc checks satisfied
        ws = workspace_path(pid)
        (ws / "repo").mkdir(parents=True, exist_ok=True)
        (ws / "repo" / "main.py").write_text("print('hi')\n")
        (ws / "repo" / "README.md").write_text("# App\n\nRun: `python main.py`\n")
        (ws / "artifacts").mkdir(parents=True, exist_ok=True)
        for name in ("README.md", "INSTALL.md", "limitations.md"):
            (ws / "artifacts" / name).write_text("# doc\n")

        decision = evaluate(db, pid, ws, is_code_project=True)
        assert decision["critical_issues"] == 0
        assert decision["decision"] != "blocked"
    finally:
        db.close()
