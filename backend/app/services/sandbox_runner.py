"""Sandbox Runner: run whitelisted commands inside the project workspace only.

Note: this is a workspace-confinement + allowlist guard, NOT a security sandbox.
Callers must never pass agent/LLM-authored commands here, and must never
*execute* agent-generated code (parse/lint only). `docker` is intentionally not
allowed — it would trivially escape to the host root. To run generated code for
real, wrap it in a container/VM/nsjail with no host secrets or network.
"""
import json
import os
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from ..config import settings

ALLOWED_BINARIES = {"python", "python3", "pip", "npm", "node", "pytest"}

# Dangerous tokens rejected anywhere in the command, even as an argument to an
# allowed binary (e.g. `python -c "os.system('curl ...')"`). Network tools,
# privilege changes, destructive ops and host-secret reads.
_BLOCKED_RE = re.compile(
    r"(?i)("
    r"\brm\s+-rf\b|\bsudo\b|\bchmod\b|\bchown\b|\bmkfs\b|\bdd\s+if=|"
    r"\bcurl\b|\bwget\b|\bncat\b|\bnetcat\b|\bssh\b|\bscp\b|\bsftp\b|\btelnet\b|"
    r"\bprintenv\b|/etc/passwd|/etc/shadow|\bshutdown\b|\breboot\b|"
    r":\(\)\s*\{|\bmkfs\b|>\s*/dev/"
    r")")


def _reject_reason(command: str, argv: list[str], workspace: Path, cwd: Path) -> str | None:
    if not argv:
        return "empty command"
    # argv[0] must be a bare command name — no path separators. Checking only
    # Path(argv[0]).name would let a caller point at an arbitrary executable
    # (e.g. "/tmp/evil/python3") that merely shares an allowed basename; the
    # bare name forces resolution through the restricted _SAFE_ENV PATH.
    if "/" in argv[0] or "\\" in argv[0] or argv[0] not in ALLOWED_BINARIES:
        return f"binary not allowed: {argv[0]}"
    if _BLOCKED_RE.search(command):
        return "blocked dangerous pattern"
    ws = workspace.resolve()
    for tok in argv[1:]:
        # for `--flag=value` check the value part; otherwise the whole token
        raw = tok.split("=", 1)[-1] if tok.startswith("-") and "=" in tok else tok
        if ".." in raw:
            return "parent-directory access"
        if raw.startswith("~"):
            return "home-directory access"
        if raw.startswith("/"):  # absolute path — allow only inside the workspace
            if not str(Path(raw).resolve()).startswith(str(ws)):
                return "absolute host path outside workspace"
    return None

# Minimal environment for child processes: the host env carries ENCRYPTION_SECRET
# and provider API keys, which generated/third-party code must never read.
_SAFE_ENV = {
    "PATH": os.getenv("PATH", "/usr/local/bin:/usr/bin:/bin"),
    "HOME": os.getenv("HOME", "/tmp"),
    "LANG": os.getenv("LANG", "C.UTF-8"),
    "PYTHONDONTWRITEBYTECODE": "1",
    "PIP_NO_INPUT": "1",
}


def run_command(workspace: Path, command: str, cwd_rel: str = "repo",
                timeout: int | None = None) -> dict:
    timeout = timeout or settings.MAX_COMMAND_RUNTIME_SECONDS
    cwd = (workspace / cwd_rel).resolve()
    if not str(cwd).startswith(str(workspace.resolve())):
        raise ValueError("sandbox cwd escapes workspace")
    cwd.mkdir(parents=True, exist_ok=True)

    try:
        argv = shlex.split(command)
    except ValueError:
        argv = []
    reason = _reject_reason(command, argv, workspace, cwd)
    if reason:
        result = {"command": command, "exit_code": -1, "status": "rejected",
                  "reason": reason, "stdout_path": None, "stderr_path": None,
                  "duration_seconds": 0}
        _log(workspace, result)
        return result

    logs_dir = workspace / "logs"
    logs_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%H%M%S")
    slug = argv[0].replace("/", "_")
    stdout_path = logs_dir / f"cmd_{slug}_{stamp}_stdout.txt"
    stderr_path = logs_dir / f"cmd_{slug}_{stamp}_stderr.txt"

    started = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=_SAFE_ENV)
        exit_code, status = proc.returncode, ("passed" if proc.returncode == 0 else "failed")
        # scrub any secret that surfaced in captured output before persisting
        stdout_path.write_text(_redact(proc.stdout or ""))
        stderr_path.write_text(_redact(proc.stderr or ""))
    except subprocess.TimeoutExpired as e:
        exit_code, status = -9, "timeout"
        stdout_path.write_text((e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or ""))
        stderr_path.write_text("timed out")
    except FileNotFoundError:
        exit_code, status = -1, "binary_not_found"
        stdout_path.write_text("")
        stderr_path.write_text(f"binary not found: {argv[0]}")

    result = {
        "command": command,
        "exit_code": exit_code,
        "stdout_path": str(stdout_path.relative_to(workspace)),
        "stderr_path": str(stderr_path.relative_to(workspace)),
        "duration_seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 2),
        "status": status,
    }
    _log(workspace, result)
    return result


def _redact(text: str) -> str:
    from ..lib.redact import redact_text
    return redact_text(text)


def _log(workspace: Path, result: dict) -> None:
    logs_dir = workspace / "logs"
    logs_dir.mkdir(exist_ok=True)
    with open(logs_dir / "command-runs.jsonl", "a") as f:
        f.write(json.dumps({**result, "at": datetime.now(timezone.utc).isoformat()}) + "\n")
