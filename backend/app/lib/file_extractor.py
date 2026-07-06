"""Extract real project files from a model's text output.

Real providers (OpenAI/Anthropic-compatible) return prose with fenced code
blocks; nothing turned that into an actual repo before. Builders are instructed
(see prompts/builder.md) to emit each file with an explicit marker:

    === FILE: path/to/file.ext ===
    ```lang
    <file contents>
    ```

Models are creative about the contract, so this module accepts every marker
shape seen in real runs:

* ``FILE: path`` / ``=== FILE: path ===`` / ``### FILE: path ===`` /
  ``**FILE: path**`` — any heading/bold decoration around the FILE keyword;
* a bare path heading right before the fence (``## src/main.py``,
  ``**src/main.py**``, `` `src/main.py` ``);
* a path in the fence info string (`` ```python path=src/main.py `` or
  `` ```src/main.py ``);
* a first-line path comment inside the block (``# src/main.py``).

Placeholder "results" (``(no changes)``, ``unchanged``, ``...``) are dropped:
an agent that changed nothing produced nothing. Paths are constrained to the
repo: absolute paths and ``..`` traversal are rejected so a prompt-injected
agent cannot write outside repo/.
"""
import re
from pathlib import PurePosixPath

_FILE_MARKER = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*{1,2}\s*)?(?:={2,}\s*)?FILE:\s*"
    r"(?P<path>[^\n=*]+?)\s*(?:={2,})?\s*(?:\*{1,2})?\s*$",
    re.IGNORECASE)
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
# first-line "# path/to/file.ext" / "// path" / "-- path" comment conventions
_PATH_COMMENT = re.compile(
    r"^\s*(?:#|//|--|;|<!--|/\*)\s*(?P<path>[\w./\-]+\.[A-Za-z0-9]{1,10})\s*(?:-->|\*/)?\s*$")
# bare path used as its own heading line: `## src/main.py`, `**main.py**`, `` `x.py` ``
_PATH_HEADING = re.compile(
    r"^\s*(?:#{1,6}\s*)?[*`\"']*(?P<path>[\w./\-]+\.[A-Za-z0-9]{1,10})[*`\"':]*\s*$")
# a path inside the fence info string: ```python path=src/main.py  /  ```src/main.py
_INFO_PATH = re.compile(
    r"(?:^|\s|=)(?:path\s*=\s*)?(?P<path>[\w./\-]+\.[A-Za-z0-9]{1,10})\s*$")

# extension-less files that are still legitimate repo files
_KNOWN_BARE_NAMES = {"Makefile", "Dockerfile", "Procfile", "LICENSE", ".gitignore",
                     ".env.example", ".dockerignore", ".editorconfig"}

# agent wrote "nothing changed" — that is not a file, it is an excuse
_PLACEHOLDER_CONTENT = re.compile(
    r"^[\s`*_\-#(\[]*(?:no\s+changes?|unchanged|no\s+update[sd]?|same\s+as\s+before|"
    r"\.{3}|see\s+above|n/?a)[\s`*_\-.)\]]*$",
    re.IGNORECASE)

# Junk workspace names agents produce when they treat the repo as a scratchpad.
# Matched against the file STEM (whole word / suffix), so legitimate names like
# template.py, config.py or test_pricing.py are untouched.
_JUNK_STEM = re.compile(
    r"(?i)"
    r"^(?:"
    r"temp\d*|tmp\d*|draft\d*|scratch\d*|untitled\d*|unused\d*|misc|stuff|"
    r"final\d+|copy\d*|backup\d*|"
    r"agent[-_]?output\d*|task[-_]?result\d*|new[-_]?component\d*"
    r")$"
    r"|^.+[-_](?:temp|tmp|draft|copy|backup|old|final\d*|v\d+|new)$")

_DELETE_MARKER = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*{1,2}\s*)?(?:={2,}\s*)?DELETE:\s*"
    r"(?P<path>[^\n=*]+?)\s*(?:={2,})?\s*(?:\*{1,2})?\s*$",
    re.IGNORECASE | re.MULTILINE)


def is_junk_filename(path: str) -> bool:
    """True for scratch/duplicate-style names (temp, draft2, utils_final,
    main_copy, agent-output…) that must never enter the deliverable repo."""
    stem = path.rsplit("/", 1)[-1]
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    return bool(_JUNK_STEM.match(stem))


def extract_deletions(text: str) -> list[str]:
    """Paths the integrator marked for removal via `=== DELETE: path ===`.
    Same path-safety rules as file creation."""
    out: list[str] = []
    for m in _DELETE_MARKER.finditer(text):
        rel = _safe_rel(m.group("path"))
        if rel and rel not in out:
            out.append(rel)
    return out

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
    if not normalized:
        return None
    # "(no changes)", "N/A", prose-with-spaces — not a real repo path
    if not re.fullmatch(r"[\w./\-]+", normalized):
        return None
    name = normalized.rsplit("/", 1)[-1]
    if "." not in name and name not in _KNOWN_BARE_NAMES:
        return None
    return normalized


def _iter_blocks(text: str):
    """Yield (label_line, info_string, code) for each fenced block; label_line
    is the raw non-blank line immediately preceding the fence (may be a FILE:
    marker), info_string is what follows the opening fence characters."""
    lines = text.splitlines()
    i = 0
    prev_nonblank = ""
    while i < len(lines):
        fence = _FENCE.match(lines[i])
        if fence:
            marker = fence.group(1)[0]
            info = fence.group(2).strip()
            closing = re.compile(r"^\s*" + re.escape(marker) + r"{3,}\s*$")
            body: list[str] = []
            i += 1
            while i < len(lines) and not closing.match(lines[i]):
                body.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            yield prev_nonblank, info, "\n".join(body)
            prev_nonblank = ""
            continue
        if lines[i].strip():
            prev_nonblank = lines[i]
        i += 1


def _path_from_label(label: str) -> str | None:
    m = _FILE_MARKER.match(label)
    if m:
        return _safe_rel(m.group("path"))
    m = _PATH_HEADING.match(label)
    if m:
        return _safe_rel(m.group("path"))
    return None


def _path_from_info(info: str) -> str | None:
    if not info:
        return None
    m = _INFO_PATH.search(info)
    if not m:
        return None
    candidate = m.group("path")
    # a bare language tag ("python", "js") never matches: _INFO_PATH requires
    # a dot extension, but "file.py" alone would — only accept it when it is
    # not the sole language token misread (e.g. ```py is filtered by the dot).
    return _safe_rel(candidate)


def is_placeholder_content(code: str) -> bool:
    """True when a "file body" is a no-op excuse rather than file contents."""
    return bool(_PLACEHOLDER_CONTENT.fullmatch(code.strip()))


def extract_repo_files(text: str) -> dict[str, str]:
    """Parse fenced blocks into {repo_relative_path: content}.

    Path resolution order: FILE marker / path heading before the block, then
    the fence info string, then a first-line path comment inside the block.
    Blocks with none of those are treated as illustrative and skipped.
    """
    files: dict[str, str] = {}
    for label, info, code in _iter_blocks(text):
        if not code.strip() or is_placeholder_content(code):
            continue
        rel = _path_from_label(label) or _path_from_info(info)
        if rel is None:
            first = code.splitlines()[0] if code else ""
            cm = _PATH_COMMENT.match(first)
            if cm:
                rel = _safe_rel(cm.group("path"))
        if rel is None or is_junk_filename(rel):
            continue  # scratch names never become deliverable files
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
