"""Access Control Engine: temporary per-phase capabilities for agents."""

ALL_RIGHTS = [
    "read_brief", "read_spec", "write_spec", "read_repo", "write_repo_branch",
    "write_review", "run_commands", "read_logs", "write_artifacts", "package_release",
]

ACCESS_BY_MANDATE: dict[str, list[str]] = {
    "lead": ["read_brief", "read_spec", "write_spec", "read_repo", "write_artifacts"],
    "critic": ["read_brief", "read_spec", "read_repo", "write_review"],
    "builder": ["read_brief", "read_spec", "read_repo", "write_repo_branch", "run_commands"],
    "reviewer": ["read_brief", "read_spec", "read_repo", "read_logs", "write_review"],
    "repairer": ["read_spec", "read_repo", "write_repo_branch", "run_commands", "read_logs"],
    "judge": ["read_brief", "read_spec", "read_repo", "read_logs", "write_review"],
    "packager": ["read_brief", "read_spec", "read_repo", "read_logs",
                 "write_artifacts", "package_release"],
}


def grant(mandate: str, phase: str) -> dict:
    access = ACCESS_BY_MANDATE.get(mandate, [])
    return {
        "phase": phase,
        "mandate": mandate,
        "access": access,
        "can_modify_code": "write_repo_branch" in access,
        "can_run_commands": "run_commands" in access,
    }


def can(grant_obj: dict, right: str) -> bool:
    return right in grant_obj.get("access", [])
