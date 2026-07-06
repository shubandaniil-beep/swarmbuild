"""Coordinator/Integrator layer: the swarm must produce ONE minimal, coherent
tree — no scratch files, no parallel implementations, no per-agent debris."""
from pathlib import Path

from app.database import SessionLocal
from app.lib.file_extractor import extract_deletions, extract_repo_files, is_junk_filename
from app.services import integration

# --------------------------------------------------------------------------- #
# file budget: junk names never become files                                   #
# --------------------------------------------------------------------------- #

def test_junk_filenames_detected():
    junk = ["temp.py", "tmp2.js", "draft.md", "final2.py", "copy.py",
            "utils_final.py", "main_copy.py", "component-old.tsx", "api_v2.py",
            "agent-output.md", "task_result.json", "new-component.tsx",
            "untitled.py", "unused.py", "src/helpers_backup.py"]
    for name in junk:
        assert is_junk_filename(name), name


def test_legitimate_filenames_pass():
    ok = ["main.py", "template.py", "config.py", "test_pricing.py",
          "components/NavBar.tsx", "finalize.py", "copyright.md",
          "newsletter.py", "storage.py", "README.md", ".env.example"]
    for name in ok:
        assert not is_junk_filename(name), name


def test_extractor_refuses_junk_files():
    text = ("=== FILE: temp.py ===\n```python\nprint('scratch')\n```\n"
            "=== FILE: main.py ===\n```python\nprint('real')\n```\n")
    assert list(extract_repo_files(text)) == ["main.py"]


def test_delete_contract_parsed():
    text = ("## Integration log\n\n"
            "=== DELETE: src/old_router.py ===\n"
            "### DELETE: utils2.py ===\n"
            "DELETE: ../outside.py\n")
    assert extract_deletions(text) == ["src/old_router.py", "utils2.py"]


# --------------------------------------------------------------------------- #
# agent manifest + integration plan contracts                                  #
# --------------------------------------------------------------------------- #

def test_agent_manifest_parsed_and_stripped():
    text = ("Some build output.\n\n"
            "```json manifest\n"
            '{"changed": "added storage layer", "files": ["storage.py"], '
            '"why": "persistence", "dependencies": ["sqlite3"], '
            '"needs_integration": ["main.py must import storage"], '
            '"risks": ["no migrations"], "do_not_create": ["db_v2.py"]}\n'
            "```\n")
    manifest = integration.parse_agent_manifest(text)
    assert manifest["files"] == ["storage.py"]
    assert manifest["needs_integration"] == ["main.py must import storage"]
    stripped = integration.strip_manifest(text)
    assert "json manifest" not in stripped
    assert "Some build output." in stripped


def test_integration_plan_parse_and_render():
    text = ("Plan:\n```json\n"
            '{"files": [{"path": "main.py", "purpose": "entry", "owner_slot": 1},'
            '{"path": "storage.py", "purpose": "db", "owner_slot": 2}],'
            '"forbidden_files": ["utils2.py"], "entry_point": "main.py"}\n```\n')
    plan = integration.parse_integration_plan(text)
    assert [f["path"] for f in plan["files"]] == ["main.py", "storage.py"]
    rendered = integration.plan_context_text(plan)
    assert "main.py" in rendered and "utils2.py" in rendered
    assert integration.parse_integration_plan("никакого json тут нет") is None


# --------------------------------------------------------------------------- #
# deterministic integration pass                                               #
# --------------------------------------------------------------------------- #

def _ws(tmp_path: Path, files: dict[str, str]) -> Path:
    for rel, content in files.items():
        p = tmp_path / "repo" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return tmp_path


def test_integration_pass_removes_junk_and_placeholders(client, tmp_path):
    ws = _ws(tmp_path, {
        "main.py": "print('real')\n",
        "temp.py": "print('scratch')\n",
        "utils.py": "(no changes)\n",
    })
    db = SessionLocal()
    try:
        report = integration.integration_pass(db, ws)
    finally:
        db.close()
    removed = {r["path"] for r in report["removed"]}
    assert removed == {"temp.py", "utils.py"}
    assert (ws / "repo" / "main.py").exists()


def test_integration_pass_collapses_exact_duplicates(client, tmp_path):
    same = "def get_price():\n    return 42\n"
    ws = _ws(tmp_path, {
        "pricing.py": same,
        "src/pricing.py": same,
        "main.py": "from pricing import get_price\n\nprint(get_price())\n",
    })
    db = SessionLocal()
    try:
        report = integration.integration_pass(db, ws)
    finally:
        db.close()
    # the referenced root copy stays canonical; the orphan duplicate is gone
    assert (ws / "repo" / "pricing.py").exists()
    assert not (ws / "repo" / "src" / "pricing.py").exists()
    assert any("identical to" in r["reason"] for r in report["removed"])


def test_integration_pass_drops_dead_stub_entrypoint(client, tmp_path):
    ws = _ws(tmp_path, {
        "main.py": "print('real entry')\n",
        "src/main.py": "# deprecated, moved to main.py\n",
    })
    db = SessionLocal()
    try:
        report = integration.integration_pass(db, ws)
    finally:
        db.close()
    assert not (ws / "repo" / "src" / "main.py").exists()
    assert any(r["reason"] == "stub entry point" for r in report["removed"])


def test_integration_pass_reports_near_duplicates_and_budget(client, tmp_path, monkeypatch):
    ws = _ws(tmp_path, {
        "api.py": "def call():\n    return 'A'\n",
        "src/api.py": "def call():\n    return 'B (different impl!)'\n",
        "main.py": "import api\n\nprint(api.call())\n",
    })
    monkeypatch.setattr(integration, "max_repo_files", lambda db: 2)
    db = SessionLocal()
    try:
        report = integration.integration_pass(db, ws)
    finally:
        db.close()
    kinds = {item["kind"] for item in report["needs_review"]}
    # different implementations are NEVER auto-deleted — reported for judgment
    assert "same_name_in_multiple_dirs" in kinds
    assert "file_budget_exceeded" in kinds
    assert (ws / "repo" / "src" / "api.py").exists()


def test_apply_deletions_is_repo_confined(client, tmp_path):
    ws = _ws(tmp_path, {"main.py": "print('x')\n", "old.py": "print('old')\n"})
    (ws / "secret-outside.txt").write_text("do not touch\n")
    removed = integration.apply_deletions(ws, ["old.py", "../secret-outside.txt"])
    assert removed == ["old.py"]
    assert (ws / "secret-outside.txt").exists()


# --------------------------------------------------------------------------- #
# orchestrator wiring: contract reaches agents, integrator runs                #
# --------------------------------------------------------------------------- #

def test_builders_receive_integration_contract_and_plan(client, monkeypatch):
    from app.models import User
    from app.providers.base import ProviderResult
    from app.services import agent_runner, phase_orchestrator
    from app.services.project_intake import create_project

    prompts: list[str] = []

    class _Capture:
        def complete(self, system, user, context=None):
            prompts.append(user)
            if "COORDINATOR" in user:
                return ProviderResult(
                    text='```json\n{"files": [{"path": "main.py", '
                         '"purpose": "entry", "owner_slot": 1}]}\n```',
                    input_tokens=10, output_tokens=10)
            if "Phase: build_sprint" in user:
                return ProviderResult(
                    text="=== FILE: main.py ===\n```python\nprint('ok')\n```\n",
                    input_tokens=10, output_tokens=10)
            # substantive prose so text phases pass the honest-progress check
            return ProviderResult(
                text=("# Отчёт по фазе\n\n" + "Содержательный анализ задачи. " * 20),
                input_tokens=10, output_tokens=10)

    monkeypatch.setattr(agent_runner, "get_provider", lambda card, key="": _Capture())

    db = SessionLocal()
    try:
        u = db.query(User).filter(User.email == "integ-wire@example.com").first()
        if not u:
            u = User(email="integ-wire@example.com", role="user", password_hash="x",
                     token_balance=1_000_000, lifetime_tokens_granted=1_000_000,
                     lifetime_tokens_spent=0, demo_generations_remaining=1)
            db.add(u)
            db.commit()
        # budget 100 → multi-agent swarm build with a coordinator plan
        project = create_project(db, "Contract wiring", "Нужен Python-скрипт.",
                                 100, ["mvp"], "code_project", "code",
                                 "non_technical", "", user_id=u.id)
        pid = project.id
    finally:
        db.close()

    run_db = SessionLocal()
    try:
        phase_orchestrator.run_project(run_db, pid)
    finally:
        run_db.close()

    build_prompts = [p for p in prompts if "build_sprint" in p
                     and "COORDINATOR" not in p and "FINAL INTEGRATOR" not in p]
    assert build_prompts, "builders never ran"
    for p in build_prompts:
        assert "INTEGRATION CONTRACT" in p          # shared file rules
        assert "ONE FUNCTION — ONE PLACE" in p
    # the coordinator plan was produced and injected into builder prompts
    assert any("COORDINATOR" in p for p in prompts)
    assert any("INTEGRATION PLAN" in p for p in build_prompts)
