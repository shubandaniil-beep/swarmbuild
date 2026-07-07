"""Scan recipes/*.md + components/*.md frontmatter and (re)generate index.json.

Frontmatter is a leading `---` block of simple `key: value` lines. List fields
(`tags`, `domain`, `style`, `colors`, `triggers`) are comma-separated. Each entry
carries a `kind`: "page" (a full-page style recipe) or "component" (a reusable
interactive block pulled in on top of a page recipe). Run after edits:
  python -m app.ui_library.build_index
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECIPES = HERE / "recipes"
COMPONENTS = HERE / "components"
INDEX = HERE / "index.json"

_LIST_FIELDS = {"tags", "domain", "style", "colors", "triggers"}


def _parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key in _LIST_FIELDS:
            fm[key] = [t.strip().lower() for t in val.split(",") if t.strip()]
        else:
            fm[key] = val
    return fm


def _scan(folder: Path, kind: str) -> list[dict]:
    entries: list[dict] = []
    if not folder.exists():
        return entries
    for path in sorted(folder.glob("*.md")):
        fm = _parse_frontmatter(path.read_text())
        if not fm.get("id"):
            continue
        # union of every searchable token → one keyword bag for cheap scoring
        keywords = sorted(set(
            fm.get("tags", []) + fm.get("domain", []) +
            fm.get("style", []) + fm.get("colors", []) + fm.get("triggers", [])
        ))
        entries.append({
            "id": fm["id"],
            "kind": fm.get("kind", kind),
            "file": f"{folder.name}/{path.name}",
            "name": fm.get("name", fm["id"]),
            "domain": fm.get("domain", []),
            "style": fm.get("style", []),
            "colors": fm.get("colors", []),
            "triggers": fm.get("triggers", []),
            "keywords": keywords,
            "summary": fm.get("summary", ""),
        })
    return entries


def build() -> list[dict]:
    entries = _scan(RECIPES, "page") + _scan(COMPONENTS, "component")
    INDEX.write_text(json.dumps({"recipes": entries}, ensure_ascii=False, indent=2))
    return entries


if __name__ == "__main__":
    built = build()
    pages = [e for e in built if e["kind"] == "page"]
    comps = [e for e in built if e["kind"] == "component"]
    print(f"indexed {len(pages)} pages + {len(comps)} components -> {INDEX}")
    for e in built:
        print(f"  [{e['kind'][:4]}] {e['id']:26} [{', '.join(e['keywords'][:6])} ...]")
