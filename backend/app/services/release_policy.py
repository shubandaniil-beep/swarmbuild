"""Release Policy Engine: honest final gate (spec §7.10)."""
from pathlib import Path

from sqlalchemy.orm import Session

from ..models import Issue


def evaluate(db: Session, project_id: str, workspace: Path, is_code_project: bool = True) -> dict:
    issues = db.query(Issue).filter(Issue.project_id == project_id).all()
    open_critical = sum(1 for i in issues if i.severity == "critical" and i.status == "open")
    major = sum(1 for i in issues if i.severity == "major")
    minor = sum(1 for i in issues if i.severity == "minor")

    checks = {
        "critical_issues_zero": open_critical == 0,
        "readme_exists": (workspace / "artifacts" / "README.md").exists()
                          or (workspace / "repo" / "README.md").exists(),
        "install_exists": (workspace / "artifacts" / "INSTALL.md").exists(),
        "final_audit_exists": (workspace / "reviews" / "final-audit.md").exists(),
        "limitations_documented": (workspace / "artifacts" / "limitations.md").exists(),
    }
    if is_code_project:
        checks["repo_exists"] = (any((workspace / "repo").iterdir())
                                 if (workspace / "repo").exists() else False)
        checks["env_example_exists"] = (workspace / "repo" / ".env.example").exists()
        checks["run_instructions_exist"] = checks["readme_exists"]
    else:
        checks["main_document_exists"] = (workspace / "artifacts" / "main-document.md").exists()

    failed = [k for k, ok in checks.items() if not ok]
    if open_critical > 0:
        decision = "blocked"
    elif failed:
        decision = "partial_release"
    else:
        decision = "release"

    return {
        "decision": decision,
        "critical_issues": open_critical,
        "major_issues": major,
        "minor_issues": minor,
        "checks": checks,
        "notes": [f"check failed: {k}" for k in failed],
    }
