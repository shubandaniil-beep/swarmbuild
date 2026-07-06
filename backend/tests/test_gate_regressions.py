"""Regression tests for the real client-facing failures that shipped as
"ready" archives before the gates existed. Each test reproduces one observed
failure mode and proves the deterministic gates now catch it."""
from pathlib import Path

from app.services import build_integrity


def _repo(ws: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        p = ws / "repo" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


def test_readme_says_python_main_but_main_missing(tmp_path):
    _repo(tmp_path, {
        "app.py": "print('the actual entry point')\n",
        "README.md": "# App\n\nRun with:\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "readme_references_real_files" in result["failed"]
    assert "readme_references_real_files" in result["hard_failed"]
    assert "main.py" in result["gates"]["readme_references_real_files"]["detail"]


def test_pandas_imported_but_not_in_requirements(tmp_path):
    _repo(tmp_path, {
        "main.py": "import pandas\n\nprint(pandas.__version__)\n",
        "requirements.txt": "requests>=2.0\n",
        "README.md": "# App\n\n```\npip install -r requirements.txt\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "imports_covered" in result["failed"]
    assert "imports_covered" in result["hard_failed"]  # blocks release
    assert "pandas" in result["gates"]["imports_covered"]["detail"]


def test_requirements_without_install_instructions_is_hard_gate(tmp_path):
    _repo(tmp_path, {
        "main.py": "print('ok')\n",
        "requirements.txt": "requests>=2.0\n",
        "README.md": "# App\n\nRun with `python main.py`.\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "install_matches_repo" in result["failed"]
    assert "install_matches_repo" in result["hard_failed"]


def test_third_party_import_with_no_requirements_at_all(tmp_path):
    _repo(tmp_path, {
        "main.py": "import flask\napp = flask.Flask(__name__)\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "imports_covered" in result["failed"]


def test_import_alias_and_transitive_deps_are_not_false_positives(tmp_path):
    _repo(tmp_path, {
        "main.py": ("import os\nfrom dotenv import load_dotenv\n"
                    "import pydantic\nfrom fastapi import FastAPI\n"
                    "import storage\n\napp = FastAPI()\n"),
        "storage.py": "import sqlite3\n\nconn = sqlite3.connect(':memory:')\n",
        "requirements.txt": "python-dotenv>=1.0\nfastapi>=0.110\n",
        "README.md": "# App\n\n```\npip install -r requirements.txt\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "imports_covered" not in result["failed"], \
        result["gates"]["imports_covered"]["detail"]


def test_sqlite3_used_without_import(tmp_path):
    _repo(tmp_path, {
        "src/main.py": ("def get_db():\n"
                        "    return sqlite3.connect('app.db')\n"),
        "main.py": "from src.main import get_db\n\nprint(get_db)\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "undefined_module_refs" in result["failed"]
    assert "undefined_module_refs" in result["hard_failed"]
    assert "sqlite3" in result["gates"]["undefined_module_refs"]["detail"]


def test_sqlite3_properly_imported_passes(tmp_path):
    _repo(tmp_path, {
        "main.py": "import sqlite3\n\nconn = sqlite3.connect(':memory:')\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "undefined_module_refs" not in result["failed"]


def test_flask_create_all_without_app_context(tmp_path):
    _repo(tmp_path, {
        "app.py": ("from flask import Flask\n"
                   "from flask_sqlalchemy import SQLAlchemy\n\n"
                   "app = Flask(__name__)\n"
                   "db = SQLAlchemy(app)\n"
                   "db.create_all()\n"),
        "requirements.txt": "flask>=3.0\nflask-sqlalchemy>=3.0\n",
        "README.md": "# App\n\n```\npip install -r requirements.txt\npython app.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "flask_app_context" in result["failed"]
    assert "flask_app_context" in result["hard_failed"]


def test_flask_create_all_inside_app_context_passes(tmp_path):
    _repo(tmp_path, {
        "app.py": ("from flask import Flask\n"
                   "from flask_sqlalchemy import SQLAlchemy\n\n"
                   "app = Flask(__name__)\n"
                   "db = SQLAlchemy(app)\n"
                   "with app.app_context():\n"
                   "    db.create_all()\n"),
        "requirements.txt": "flask>=3.0\nflask-sqlalchemy>=3.0\n",
        "README.md": "# App\n\n```\npip install -r requirements.txt\npython app.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "flask_app_context" not in result["failed"]


def test_conflicting_unrelated_implementations_block_release(tmp_path):
    _repo(tmp_path, {
        "app.py": "print('implementation A — flask style')\n",
        "src/main.py": "print('implementation B — completely unrelated')\n",
        "README.md": "# App\n\n```\npython app.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "no_conflicting_entrypoints" in result["failed"]
    assert "no_conflicting_entrypoints" in result["hard_failed"]


def test_related_entrypoints_pass(tmp_path):
    _repo(tmp_path, {
        "main.py": "from src.main import run\n\nrun()\n",
        "src/main.py": "def run():\n    print('ok')\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "no_conflicting_entrypoints" not in result["failed"]


def test_placeholder_file_blocks_release(tmp_path):
    _repo(tmp_path, {
        "main.py": "print('ok')\n",
        "utils.py": "(no changes)\n",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert "no_placeholder_files" in result["failed"]
    assert "utils.py" in result["gates"]["no_placeholder_files"]["detail"]


# --------------------------------------------------------------------------- #
# code hidden inside documents                                                #
# --------------------------------------------------------------------------- #

def test_code_in_main_document_is_salvaged_into_repo(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "repo").mkdir()
    (tmp_path / "artifacts" / "main-document.md").write_text(
        "# Проект\n\nВот реализация:\n\n"
        "=== FILE: main.py ===\n```python\nprint('salvaged')\n```\n\n"
        "### FILE: requirements.txt ===\n```\nrequests>=2.0\n```\n")
    salvaged = build_integrity.salvage_files_from_documents(tmp_path)
    assert set(salvaged) == {"main.py", "requirements.txt"}
    assert (tmp_path / "repo" / "main.py").read_text() == "print('salvaged')\n"


def test_salvage_never_overwrites_contract_files(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "repo").mkdir()
    (tmp_path / "repo" / "main.py").write_text("print('from build contract')\n")
    (tmp_path / "artifacts" / "main-document.md").write_text(
        "FILE: main.py\n```python\nprint('stale copy in doc')\n```\n")
    salvaged = build_integrity.salvage_files_from_documents(tmp_path)
    assert salvaged == {}
    assert "build contract" in (tmp_path / "repo" / "main.py").read_text()


def test_document_project_with_file_markers_fails_gate(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "main-document.md").write_text(
        "# Документ\n\n" + ("Основное содержание документа. " * 30) +
        "\n\nFILE: main.py\n```python\nprint('code that should be a repo file')\n```\n")
    result = build_integrity.run_gates(tmp_path, is_code_project=False)
    assert "main_document_present" in result["failed"]
    assert "unextracted" in result["gates"]["main_document_present"]["detail"]


def test_document_project_stub_fails_gate(tmp_path):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "main-document.md").write_text("# Заглушка\n\nTBD\n")
    result = build_integrity.run_gates(tmp_path, is_code_project=False)
    assert result["passed"] is False


def test_valid_repo_still_passes_all_gates(tmp_path):
    _repo(tmp_path, {
        "main.py": ("import argparse\nimport sqlite3\n\n"
                    "def main():\n    print(sqlite3.sqlite_version)\n\n"
                    "if __name__ == '__main__':\n    main()\n"),
        "requirements.txt": "",
        "README.md": "# App\n\n```\npython main.py\n```\n",
    })
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "INSTALL.md").write_text("Просто запустите `python main.py`.\n")
    result = build_integrity.run_gates(tmp_path, is_code_project=True)
    assert result["passed"] is True, result["failed"]
