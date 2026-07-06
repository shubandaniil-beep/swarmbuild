"""Round-2 regressions: post-processing must not break code, gates must judge
the final tree, stale reviews must not block fresh repos, restarts must
self-heal, and the model catalog must track the provider."""
import ast
import io
import zipfile
from pathlib import Path

from app.database import SessionLocal
from app.lib.redact import redact
from app.models import Event, Issue, User
from app.services import build_integrity
from app.services.project_intake import create_project, workspace_path


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


# --------------------------------------------------------------------------- #
# 1-2. redaction is syntax-safe and gates see the final tree                   #
# --------------------------------------------------------------------------- #

def test_redaction_never_breaks_python_syntax():
    code = ("import os\n"
            "SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')\n"
            "ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')\n"
            "API_KEY = \"gsk_real1234567890abcdef\"\n"
            "TOKEN = None\n"
            "if not API_KEY:\n"
            "    raise SystemExit(1)\n")
    out, found = redact(code)
    ast.parse(out)  # must stay valid Python
    # env-reading expressions are untouched — they contain no secret
    assert "os.environ.get('FLASK_SECRET_KEY')" in out
    assert "os.getenv('ALPHA_VANTAGE_API_KEY')" in out
    assert "TOKEN = None" in out
    # the actual literal secret is gone, quoting preserved
    assert "gsk_real1234567890abcdef" not in out
    assert 'API_KEY = "[REDACTED]"' in out
    assert found == ["assigned_api_key"]


def test_env_file_values_still_redacted():
    out, found = redact("API_KEY=abcdef123456789\nDEBUG=true\n")
    assert "[REDACTED]" in out
    assert "abcdef123456789" not in out
    assert "DEBUG=true" in out


def test_scan_and_redact_reports_syntax_breakage(tmp_path):
    """If redaction ever corrupts a previously-valid .py, the scanner must say
    so — the final-tree gates then block the release instead of shipping it."""
    from app.services.secret_scanner import scan_and_redact
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "settings.py").write_text(
        'API_KEY = "gsk_real1234567890abcdef"\n')
    summary = scan_and_redact(tmp_path)
    assert summary["findings"]
    # our syntax-safe redactor keeps the file valid → nothing reported broken
    assert summary["syntax_broken_by_redaction"] == []
    ast.parse((tmp_path / "repo" / "settings.py").read_text())


def _package_project(title: str, repo_files: dict[str, str]):
    uid = _make_user("pack-user@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, title, "Нужен рабочий скрипт.", 1, ["mvp"],
                                 "code_project", "code", "non_technical", "",
                                 user_id=uid)
        pid = project.id
        ws = workspace_path(pid)
        for rel, content in repo_files.items():
            p = ws / "repo" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        from app.services.artifact_packager import package
        zip_path, decision = package(db, project, ws)
        return pid, ws, zip_path, decision
    finally:
        db.close()


def test_zip_ships_exactly_what_the_gates_approved(client):
    """The archive must be byte-identical to the on-disk final tree — no
    transformation may happen at zip time after the release decision."""
    _, ws, zip_path, decision = _package_project("Final tree", {
        "main.py": "print('ok')\n",
        "README.md": "# App\n\nRun `python main.py`.\n",
    })
    archive = zipfile.ZipFile(io.BytesIO(zip_path.read_bytes()))
    for name in archive.namelist():
        on_disk = ws / name
        assert on_disk.exists(), name
        assert archive.read(name) == on_disk.read_bytes(), name


def test_install_md_describes_the_actual_tree(client):
    """INSTALL must not send the user to files that do not exist."""
    _, ws, _, _ = _package_project("Install honesty", {
        "main.py": "print('ok')\n",
        "README.md": "# App\n\nRun `python main.py`.\n",
    })
    install = (ws / "artifacts" / "INSTALL.md").read_text()
    # no requirements.txt and no .env.example in this repo → no such steps
    assert "pip install" not in install
    assert ".env.example" not in install


def test_install_gate_catches_missing_env_example(tmp_path):
    (tmp_path / "repo").mkdir(parents=True)
    (tmp_path / "repo" / "main.py").write_text("print('ok')\n")
    (tmp_path / "repo" / "README.md").write_text(
        "# App\n\nCopy `.env.example` to `.env`, then `python main.py`.\n")
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "install_matches_repo" in result["failed"]


# --------------------------------------------------------------------------- #
# 4-5. stub entrypoints + cross-file consistency                               #
# --------------------------------------------------------------------------- #

def _repo(ws: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = ws / "repo" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_deprecated_stub_is_not_a_conflicting_entrypoint(tmp_path):
    _repo(tmp_path, {
        "main.py": "print('the real implementation')\n",
        "src/main.py": "# deprecated, see main.py\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "no_conflicting_entrypoints" not in result["failed"]


def test_empty_body_stub_is_not_a_conflicting_entrypoint(tmp_path):
    _repo(tmp_path, {
        "app.py": "print('real')\n",
        "src/app.py": '"""Old module kept for history."""\nimport os\npass\n',
        "README.md": "# App\n\n```\npython app.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "no_conflicting_entrypoints" not in result["failed"]


def test_import_of_missing_local_name_blocks_release(tmp_path):
    _repo(tmp_path, {
        "main.py": "from storage import get_current_oil_price\n\n"
                   "print(get_current_oil_price())\n",
        "storage.py": "def get_oil_price():\n    return 42\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "local_imports_resolve" in result["failed"]
    assert "local_imports_resolve" in result["hard_failed"]
    assert "get_current_oil_price" in result["gates"]["local_imports_resolve"]["detail"]


def test_matching_local_import_passes(tmp_path):
    _repo(tmp_path, {
        "main.py": "from storage import get_oil_price\n\nprint(get_oil_price())\n",
        "storage.py": "def get_oil_price():\n    return 42\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "local_imports_resolve" not in result["failed"]


def test_wrong_call_arity_blocks_release(tmp_path):
    _repo(tmp_path, {
        "pricing.py": "def calculate_fuel_price(base, tax):\n"
                      "    return base + tax\n",
        "test_pricing.py": "from pricing import calculate_fuel_price\n\n"
                           "assert calculate_fuel_price(100) == 100\n",
        "main.py": "from pricing import calculate_fuel_price\n\n"
                   "print(calculate_fuel_price(100, 20))\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "call_arity_ok" in result["failed"]
    assert "calculate_fuel_price" in result["gates"]["call_arity_ok"]["detail"]


def test_correct_arity_and_defaults_pass(tmp_path):
    _repo(tmp_path, {
        "pricing.py": "def calc(base, tax=0, *extras):\n    return base + tax\n",
        "main.py": "from pricing import calc\n\n"
                   "print(calc(1))\nprint(calc(1, 2))\nprint(calc(1, 2, 3, 4))\n"
                   "print(calc(base=5, tax=1))\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "call_arity_ok" not in result["failed"], \
        result["gates"]["call_arity_ok"]["detail"]


# --------------------------------------------------------------------------- #
# 3. stale review issues are revalidated against the current repo              #
# --------------------------------------------------------------------------- #

def test_stale_missing_file_issues_are_closed(client):
    from app.services.phase_orchestrator import _revalidate_open_issues
    uid = _make_user("stale-user@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, "Stale review", "brief", 1, ["mvp"],
                                 "code_project", "code", "non_technical", "",
                                 user_id=uid)
        pid = project.id
        ws = workspace_path(pid)
        (ws / "repo").mkdir(parents=True, exist_ok=True)
        (ws / "repo" / "app.py").write_text("print('now exists')\n")
        db.add(Issue(project_id=pid, phase_key="review_stop", severity="major",
                     title="Flask app missing",
                     description="app.py not found — the API layer is absent."))
        db.add(Issue(project_id=pid, phase_key="review_stop", severity="major",
                     title="Weak error handling",
                     description="try/except blocks are too broad."))
        db.commit()

        closed = _revalidate_open_issues(db, project, ws)
        assert closed == 1
        issues = {i.title: i.status for i in
                  db.query(Issue).filter(Issue.project_id == pid).all()}
        assert issues["Flask app missing"] == "fixed"       # file exists now
        assert issues["Weak error handling"] == "open"      # still a real claim
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# 6. backend restart auto-resumes interrupted projects                         #
# --------------------------------------------------------------------------- #

def test_restart_requeues_interrupted_project(client, monkeypatch):
    from app.services import registry_seed
    from app.workers import project_worker

    enqueued: list[str] = []
    monkeypatch.setattr(project_worker, "enqueue", lambda pid: enqueued.append(pid))

    uid = _make_user("resume-user@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, "Interrupted", "brief", 1, ["mvp"],
                                 "code_project", "code", "non_technical", "",
                                 user_id=uid)
        pid = project.id
        project.status = "running"
        project.current_phase = "build_sprint"
        db.commit()

        registry_seed._mark_interrupted_projects(db)
        db.refresh(project)
        assert project.status == "queued"          # resumed, not failed
        assert pid in enqueued
        events = [e.event_type for e in
                  db.query(Event).filter(Event.project_id == pid).all()]
        assert "worker_resumed" in events
        assert "worker_interrupted" not in events  # no client-facing failure
    finally:
        db.close()


def test_restart_crash_loop_parks_project_as_failed(client, monkeypatch):
    from app.services import registry_seed
    from app.workers import project_worker

    monkeypatch.setattr(project_worker, "enqueue", lambda pid: None)
    uid = _make_user("resume-user2@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, "Crash loop", "brief", 1, ["mvp"],
                                 "code_project", "code", "non_technical", "",
                                 user_id=uid)
        pid = project.id
        project.status = "running"
        for _ in range(registry_seed._MAX_AUTO_RESUMES):
            db.add(Event(project_id=pid, event_type="worker_resumed",
                         message="resumed", meta={}))
        db.commit()

        registry_seed._mark_interrupted_projects(db)
        db.refresh(project)
        assert project.status == "failed"
        events = [e.event_type for e in
                  db.query(Event).filter(Event.project_id == pid).all()]
        assert "worker_resume_exhausted" in events
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# 7. client sees the credit economy, never raw internal spend                  #
# --------------------------------------------------------------------------- #

def test_client_budget_view_is_credit_based(client):
    from fastapi.testclient import TestClient

    from app.lib.security import create_token
    from app.main import app

    uid = _make_user("credit-view@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, "Credit view", "brief", 1, ["mvp"],
                                 "code_project", "code", "non_technical", "",
                                 user_id=uid)
        pid = project.id
        project.credits_spent = 40
        db.commit()
    finally:
        db.close()

    c = TestClient(app)
    headers = {"Authorization": f"Bearer {create_token(uid, 0)}"}
    payload = c.get(f"/api/projects/{pid}", headers=headers).json()
    budget = payload["budget"]
    assert budget["credits_spent"] == 40
    assert "credits_allocated" in budget
    assert "credits_remaining_in_package" in budget
    # spent_usd is derived from burned credits, not internal provider cost
    assert budget["spent_usd"] == 0.4
    # internal budget split never leaks to a client
    assert "model_budget_usd" not in budget
    assert "platform_fee_usd" not in budget


# --------------------------------------------------------------------------- #
# 10. rotation: a model never approves its own work through a virtual slot     #
# --------------------------------------------------------------------------- #

def test_rotation_checkers_use_a_different_route_when_available():
    from app.services.role_rotation import _route, build_rotation_plan

    def card(model, virtual=""):
        return {"id": f"{model}{virtual}", "provider_id": "prov-groq",
                "model_name": model, "provider": "groq", "cost_level": "low"}

    # 4 slots over 2 real routes (each duplicated as a virtual agent)
    pool = [card("llama-70b"), card("llama-8b"),
            card("llama-70b", "_v2"), card("llama-8b", "_v2")]
    phases = ["build_sprint", "review_stop", "final_audit"]
    plan = build_rotation_plan(phases, pool)

    for phase_plan in plan:
        assignments = {a["mandate"]: a for a in phase_plan["assignments"]}
        author = assignments.get("lead") or assignments.get("builder")
        if author is None:
            continue
        for mandate in ("judge", "reviewer"):
            checker = assignments.get(mandate)
            if checker is None:
                continue
            assert _route(checker["card"]) != _route(author["card"]), \
                (phase_plan["phase"], mandate)


# --------------------------------------------------------------------------- #
# 9. Groq catalog sync                                                         #
# --------------------------------------------------------------------------- #

def test_groq_catalog_sync_reconciles_registry(client, monkeypatch):
    from app.models import ModelEntry, Provider
    from app.services import key_pool, model_catalog

    live = [
        {"id": "llama-3.3-70b-versatile", "active": True,
         "context_window": 131072, "max_completion_tokens": 32768},
        {"id": "brand-new-preview-model", "active": True, "context_window": 8192},
        {"id": "whisper-large-v3", "active": True, "context_window": 448},
    ]
    monkeypatch.setattr(model_catalog, "fetch_provider_models",
                        lambda base_url, key, timeout=15.0: live)

    db = SessionLocal()
    try:
        provider = Provider(name="Groq-Sync-Test", provider_type="groq",
                            base_url="https://api.groq.com/openai/v1",
                            enabled=True, status="active", priority=10)
        db.add(provider)
        db.commit()
        key_pool.add_keys(db, provider, "gsk-test-key-1")
        # a model we track that the provider no longer serves
        db.add(ModelEntry(display_name="Groq Old Model", provider_id=provider.id,
                          model_name="llama2-70b-4096", enabled=True))
        db.commit()

        summary = model_catalog.sync_groq_models(db, provider)

        entries = {m.model_name: m for m in db.query(ModelEntry)
                   .filter(ModelEntry.provider_id == provider.id).all()}
        # known production model: added, priced, enabled
        prod = entries["llama-3.3-70b-versatile"]
        assert prod.enabled is True
        assert float(prod.input_price_per_1m) == 0.59
        assert prod.max_output_tokens == 8192  # capped
        # unpriced preview model: registered but never enabled silently
        preview = entries["brand-new-preview-model"]
        assert preview.enabled is False
        assert "unpriced" in preview.display_name
        # deprecated model: disabled, kept for history
        old = entries["llama2-70b-4096"]
        assert old.enabled is False
        assert "deprecated" in old.display_name
        # non-chat models never enter the pool
        assert "whisper-large-v3" not in entries
        assert "whisper-large-v3" in summary["skipped_non_chat"]
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# 11. automatic recovery from a blocked/partial packaging verdict              #
# --------------------------------------------------------------------------- #

def test_release_recovery_repairs_gate_failure_and_releases(client, monkeypatch):
    from app.models import ProjectPhase
    from app.providers.base import ProviderResult
    from app.services import phase_orchestrator

    def repairer_stub(db, ws, project, phase_key, assignment, agent_db_id,
                      extra_context=None, retry=True):
        # the concrete gate error is in the prompt context; fix exactly it
        fixed_readme = "# App\n\nRun:\n```\npython main.py\n```\n"
        return ProviderResult(text="repair done", input_tokens=10, output_tokens=10,
                              files={"README.md": fixed_readme}), 0.001

    monkeypatch.setattr(phase_orchestrator, "run_agent", repairer_stub)

    uid = _make_user("recovery-user@example.com")
    db = SessionLocal()
    try:
        project = create_project(db, "Recovery", "brief", 1, ["mvp"],
                                 "code_project", "code", "non_technical", "",
                                 user_id=uid)
        pid = project.id
        ws = workspace_path(pid)
        (ws / "repo").mkdir(parents=True, exist_ok=True)
        (ws / "repo" / "main.py").write_text("print('ok')\n")
        # README references a ghost file → readme gate fails → not releasable
        (ws / "repo" / "README.md").write_text(
            "# App\n\nRun `python ghost.py`.\n")

        from app.services.artifact_packager import package
        _, decision = package(db, project, ws)
        assert decision["decision"] != "release"

        phase = (db.query(ProjectPhase)
                 .filter(ProjectPhase.project_id == pid,
                         ProjectPhase.phase_key == "packaging").first())
        assignment = {"model_id": "m1", "model_name": "test-model",
                      "provider": "mock", "mandate": "packager", "agent_slot": 1,
                      "access": [], "card": {"id": "m1", "provider": "mock",
                                             "provider_id": None,
                                             "model_name": "test-model",
                                             "cost_level": "free"}}
        new_decision, _ = phase_orchestrator._attempt_release_recovery(
            db, project, ws, phase, [assignment], {}, True, decision)
        assert new_decision["decision"] == "release", new_decision["notes"]
    finally:
        db.close()
