"""Extract real project files from a model's text output.

Real providers (OpenAI/Anthropic-compatible) return prose with fenced code
blocks; nothing turned that into an actual repo before. Builders are instructed
(see prompts/builder.md) to emit each file with an explicit marker:

    === FILE: path/to/file.ext ===
    ```lang
    <file contents>
    ```

This module parses that contract, and falls back to a first-line path comment
(`# path/to/file.py`) inside fenced blocks for models that ignore the marker.
Paths are constrained to the repo: absolute paths and `..` traversal are
dropped so a prompt-injected agent cannot write outside repo/.
"""
import re
from pathlib import PurePosixPath

_FILE_MARKER = re.compile(r"^\s*(?:={2,}\s*)?FILE:\s*(?P<path>[^\n=]+?)\s*(?:={2,})?\s*$",
                          re.IGNORECASE)
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
# first-line "# path/to/file.ext" / "// path" / "-- path" comment conventions
_PATH_COMMENT = re.compile(
    r"^\s*(?:#|//|--|;|<!--|/\*)\s*(?P<path>[\w./\-]+\.[A-Za-z0-9]{1,10})\s*(?:-->|\*/)?\s*$")

_MAX_FILES = 60
_MAX_FILE_BYTES = 200_000


def _safe_rel(path: str) -> str | None:
    """Normalize an agent-supplied path to a safe repo-relative path, or None."""
    path = (path or "").strip().strip("`\"'").replace("\\", "/")
    if not path:
        return None
    # strip a leading repo/ or ./ the model may have included
    path = re.sub(r"^\.?/", "", path)
    path = re.sub(r"^repo/", "", path)
    if not path or path.startswith("/") or ":" in path.split("/")[0]:
        return None
    parts = PurePosixPath(path).parts
    if any(p == ".." for p in parts):
        return None
    normalized = "/".join(p for p in parts if p not in ("", "."))
    return normalized or None


def _iter_blocks(text: str):
    """Yield (label_line, code) for each fenced block; label_line is the raw
    non-blank line immediately preceding the fence (may be a FILE: marker)."""
    lines = text.splitlines()
    i = 0
    prev_nonblank = ""
    while i < len(lines):
        fence = _FENCE.match(lines[i])
        if fence:
            marker = fence.group(1)[0]
            closing = re.compile(r"^\s*" + re.escape(marker) + r"{3,}\s*$")
            body: list[str] = []
            i += 1
            while i < len(lines) and not closing.match(lines[i]):
                body.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            yield prev_nonblank, "\n".join(body)
            prev_nonblank = ""
            continue
        if lines[i].strip():
            prev_nonblank = lines[i]
        i += 1


def extract_repo_files(text: str) -> dict[str, str]:
    """Parse fenced blocks into {repo_relative_path: content}.

    Uses the `FILE:` marker preceding a block when present, otherwise a
    first-line path comment inside the block. Blocks with neither are treated
    as illustrative and skipped.
    """
    files: dict[str, str] = {}
    for label, code in _iter_blocks(text):
        if not code.strip():
            continue
        rel = None
        m = _FILE_MARKER.match(label)
        if m:
            rel = _safe_rel(m.group("path"))
        if rel is None:
            first = code.splitlines()[0] if code else ""
            cm = _PATH_COMMENT.match(first)
            if cm:
                rel = _safe_rel(cm.group("path"))
        if rel is None:
            continue
        content = code
        if len(content.encode("utf-8", "replace")) > _MAX_FILE_BYTES:
            content = content.encode("utf-8", "replace")[:_MAX_FILE_BYTES].decode(
                "utf-8", "ignore") + "\n"
        if not content.endswith("\n"):
            content += "\n"
        files[rel] = content
        if len(files) >= _MAX_FILES:
            break
    return files
