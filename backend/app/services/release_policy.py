"""Release Policy Engine: honest final gate (spec §7.10).

The decision is the client's trust boundary: only "release" allows a paying
user to download project.zip. It combines two independent sources of truth —

* open critical issues + presence of the required deliverable documents, and
* deterministic build gates (dependencies parse, code parses, entry point
  exists, install/README match the real repo) from `build_integrity`.

A full "release" needs BOTH: no open critical issues, all document checks, and
every hard build gate green. Anything short of that is "partial_release" (or
"blocked" when critical issues are open) — never downloadable by the client.
"""
import json
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Issue, ProjectPhase
from . import build_integrity


def _planned_phases(db: Session, project_id: str, workspace: Path) -> set[str]:
    """Which phases this project's tier actually promised. A cheaper tier that
    legitimately has no `final_audit` phase must not be judged for a missing
    final-audit artifact — only phases in the plan are required to leave one."""
    plan = workspace / "phase_plan.json"
    if plan.exists():
        try:
            data = json.loads(plan.read_text())
            keys = {p.get("phase_id") for p in data.get("phases", []) if p.get("phase_id")}
            if keys:
                return keys
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return {p.phase_key for p in
            db.query(ProjectPhase).filter(ProjectPhase.project_id == project_id).all()}


_ENV_USE_MARKERS = ("os.environ", "getenv", "load_dotenv", "process.env", "dotenv")


def _uses_env(repo: Path) -> bool:
    if not repo.exists():
        return False
    for f in repo.rglob("*"):
        if f.suffix not in (".py", ".js", ".ts"):
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        if any(marker in text for marker in _ENV_USE_MARKERS):
            return True
    return False


def evaluate(db: Session, project_id: str, workspace: Path, is_code_project: bool = True) -> dict:
    issues = db.query(Issue).filter(Issue.project_id == project_id).all()
    open_critical = sum(1 for i in issues if i.severity == "critical" and i.status == "open")
    major = sum(1 for i in issues if i.severity == "major")
    minor = sum(1 for i in issues if i.severity == "minor")
    planned = _planned_phases(db, project_id, workspace)

    checks = {
        "critical_issues_zero": open_critical == 0,
        "readme_exists": (workspace / "artifacts" / "README.md").exists()
                          or (workspace / "repo" / "README.md").exists(),
        "install_exists": (workspace / "artifacts" / "INSTALL.md").exists(),
        "limitations_documented": (workspace / "artifacts" / "limitations.md").exists(),
    }
    # Only require a final-audit artifact when the tier actually runs that phase.
    if "final_audit" in planned:
        checks["final_audit_exists"] = (workspace / "reviews" / "final-audit.md").exists()
    if is_code_project:
        checks["repo_exists"] = (any((workspace / "repo").iterdir())
                                 if (workspace / "repo").exists() else False)
        # .env.example is only owed when the code actually reads configuration
        # from the environment; a stdlib-only CLI without env use must not be
        # held back for a file it has no reason to ship.
        checks["env_example_exists"] = ((workspace / "repo" / ".env.example").exists()
                                        or not _uses_env(workspace / "repo"))
        checks["run_instructions_exist"] = checks["readme_exists"]
    else:
        checks["main_document_exists"] = (workspace / "artifacts" / "main-document.md").exists()

    # deterministic build gates — the "does it actually run as documented" half.
    gate_result = build_integrity.run_gates(workspace, is_code_project)
    for name, gate in gate_result["gates"].items():
        checks[f"gate_{name}"] = gate["passed"]

    failed = [k for k, ok in checks.items() if not ok]
    hard_gate_failed = bool(gate_result["hard_failed"])

    if open_critical > 0:
        decision = "blocked"
    elif failed or hard_gate_failed:
        decision = "partial_release"
    else:
        decision = "release"

    notes = [f"check failed: {k}" for k in failed]
    for name in gate_result["failed"]:
        notes.append(f"build gate failed: {name} — {gate_result['gates'][name]['detail']}")

    return {
        "decision": decision,
        "critical_issues": open_critical,
        "major_issues": major,
        "minor_issues": minor,
        "checks": checks,
        "gates": gate_result["gates"],
        "gate_failures": gate_result["failed"],
        "hard_gate_failures": gate_result["hard_failed"],
        "notes": notes,
    }
