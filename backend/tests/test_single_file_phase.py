"""single_file phase: a strong-model finishing pass that fuses a web build into
ONE self-contained index.html — appended to every tier, free to the client, and
gated so backend/CLI projects skip it."""
from pathlib import Path

from app.lib.file_extractor import extract_deletions
from app.services import budget_engine, credit_pricing, integration, role_rotation
from app.services.access_control import ACCESS_BY_MANDATE
from app.services.phase_orchestrator import _web_source_bundle


def test_single_file_in_every_tier_before_packaging():
    for tier in (budget_engine.SHORT_PHASES, budget_engine.BASIC_PHASES,
                 budget_engine.FULL_PHASES):
        assert "single_file" in tier
        assert tier.index("single_file") == tier.index("packaging") - 1


def test_assembler_wiring():
    assert role_rotation.PHASE_MANDATES["single_file"] == ["assembler"]
    assert "single_file" in role_rotation._AUTHOR_PHASES
    assert role_rotation._PRIMARY_AUTHOR["single_file"] == "assembler"
    access = ACCESS_BY_MANDATE["assembler"]
    assert "read_repo" in access and "write_repo_branch" in access
    assert Path("app/prompts/assembler.md").exists()


def test_single_file_is_free():
    keys = budget_engine.FULL_PHASES
    assert credit_pricing.phase_credits("single_file", keys, 5000) == 0
    # a zero-weight phase must contribute exactly nothing to the client's bill:
    # the total is identical whether or not single_file is in the pipeline.
    without = [k for k in keys if k != "single_file"]
    total_with = sum(credit_pricing.phase_credits(p, keys, 5000) for p in keys)
    total_without = sum(credit_pricing.phase_credits(p, without, 5000) for p in without)
    assert total_with == total_without


def test_web_source_bundle_reads_web_files(tmp_path):
    repo = tmp_path / "repo"
    (repo).mkdir()
    (repo / "index.html").write_text("<html><body>hi</body></html>")
    (repo / "styles.css").write_text(".a{color:red}")
    (repo / "app.js").write_text("console.log(1)")
    (repo / "data.py").write_text("x = 1")  # non-web: ignored
    bundle = _web_source_bundle(tmp_path)
    assert set(bundle) == {"index.html", "styles.css", "app.js"}
    assert "color:red" in bundle["styles.css"]


def test_delete_markers_drive_single_file_cleanup(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "index.html").write_text("<html>final</html>")
    (repo / "styles.css").write_text(".a{}")
    (repo / "app.js").write_text("x")
    text = "=== FILE: index.html ===\n```\n<html>final</html>\n```\n" \
           "DELETE: styles.css\nDELETE: app.js\n"
    integration.apply_deletions(tmp_path, extract_deletions(text))
    remaining = {p.name for p in repo.iterdir()}
    assert remaining == {"index.html"}
