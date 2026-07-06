"""Secret scanning for generated artifacts, run before packaging.

Walks the repo/artifacts, redacts any real secret in place (replacing with a
placeholder), converts a real `.env` into `.env.example`, and returns a findings
summary that feeds the security report and artifact safety status.
"""
from pathlib import Path

from ..lib.redact import redact

# only scan text-like files; binaries are shipped as-is
_TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
                  ".env", ".example", ".py", ".js", ".ts", ".tsx", ".jsx", ".sh",
                  ".html", ".css", ".sql", ".conf", ".properties", ""}
_MAX_FILE_BYTES = 2_000_000


def _is_scannable(f: Path) -> bool:
    if not f.is_file():
        return False
    if f.name == "project.zip":
        return False
    if f.suffix.lower() not in _TEXT_SUFFIXES and not f.name.startswith(".env"):
        return False
    try:
        return f.stat().st_size <= _MAX_FILE_BYTES
    except OSError:
        return False


def scan_and_redact(workspace: Path) -> dict:
    """Redact secrets across the shippable tree. Returns a findings summary."""
    roots = [workspace / "repo", workspace / "artifacts"]
    findings: list[dict] = []
    labels: set[str] = set()
    files_scanned = 0
    files_redacted = 0

    for root in roots:
        if not root.exists():
            continue
        for f in sorted(root.rglob("*")):
            if not _is_scannable(f):
                continue
            files_scanned += 1
            try:
                original = f.read_text(errors="replace")
            except OSError:
                continue
            cleaned, found = redact(original)
            if found:
                labels.update(found)
                rel = str(f.relative_to(workspace))
                findings.append({"file": rel, "types": found})
                if cleaned != original:
                    f.write_text(cleaned)
                    files_redacted += 1
            # A shipped project must never carry a real `.env` — move its
            # (already-redacted) content to `.env.example` and drop the
            # original, regardless of whether a secret was actually found in
            # it: presence of `.env` in the archive is itself the risk.
            if f.name == ".env":
                example = f.with_name(".env.example")
                if not example.exists():
                    example.write_text(cleaned)
                f.unlink()

    return {
        "files_scanned": files_scanned,
        "files_redacted": files_redacted,
        "secret_types": sorted(labels),
        "findings": findings,
        "clean": not findings,
    }
