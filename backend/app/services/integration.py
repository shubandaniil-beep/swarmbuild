"""Coordinator / Integrator layer — the swarm speaks with one voice.

Individual agents are good at producing material and terrible at producing a
coherent whole. This module is the architectural glue the pipeline runs on:

* **Integration contract** (`file_rules_text`) — one shared instruction every
  agent receives: what already exists, the file budget, junk-name bans, the
  one-function-one-place rule, and the structured manifest each agent owes.
* **Integration plan** (`plan_task_text` / `parse_integration_plan`) — before
  builders run, the coordinator produces a single file plan with owners, so
  two agents never build alternative implementations of the same thing.
* **Agent manifest** (`parse_agent_manifest`) — agents return structured
  results (what changed, why, dependencies, integration needs, risks), not
  free text; the integrator consumes these, the user never sees them.
* **Integration pass** (`integration_pass`) — a deterministic sweep over the
  final tree: junk/placeholder files removed, exact duplicates collapsed,
  stub entry points dropped, near-duplicates and budget overruns reported for
  the LLM integrator to resolve.

The user-facing result is always ONE integrated tree + one report — never a
pile of per-agent fragments.
"""
import hashlib
import json
import re
from pathlib import Path

from sqlalchemy.orm import Session

from ..lib.file_extractor import is_junk_filename, is_placeholder_content
from .settings_service import get_setting

_DEFAULT_MAX_REPO_FILES = 40

_MANIFEST_FENCE = re.compile(r"```json\s+manifest\s*\n(.*?)\n```", re.S | re.I)
_PLAN_FENCE = re.compile(r"```json\s*\n(\{.*?\})\s*\n```", re.S)

MANIFEST_KEYS = ("changed", "files", "why", "dependencies",
                 "needs_integration", "risks", "do_not_create")


# --------------------------------------------------------------------------- #
# shared contract injected into every agent prompt                             #
# --------------------------------------------------------------------------- #

def max_repo_files(db: Session) -> int:
    return int(get_setting(db, "max_repo_files") or _DEFAULT_MAX_REPO_FILES)


def file_rules_text(db: Session, existing_files: list[str]) -> str:
    budget = max_repo_files(db)
    existing = "\n".join(f"- {f}" for f in existing_files[:80]) or "- (repo is empty)"
    return (
        "INTEGRATION CONTRACT (mandatory):\n"
        f"Existing repo files — EXTEND these instead of creating parallel ones:\n{existing}\n\n"
        "Rules:\n"
        "1. MINIMUM FILES. Prefer editing an existing file over creating a new one. "
        f"The whole repo must stay under {budget} files.\n"
        "2. A new file is allowed only when the architecture genuinely needs it; "
        "state in your manifest why no existing file could host the change.\n"
        "3. FORBIDDEN names: temp, tmp, draft, scratch, final2, copy, backup, old, "
        "new-component, agent-output, task-result, untitled, unused, *_v2 — such "
        "files are discarded automatically.\n"
        "4. ONE FUNCTION — ONE PLACE. Never create an alternative implementation of "
        "something that already exists (a second router, a second API client, a "
        "second config, a second entry point). Modify the existing one.\n"
        "5. You produce MATERIAL for the integrator, not the final deliverable. "
        "The coordinator merges, deduplicates and finalizes.\n\n"
        "After your output, append a structured manifest in this exact fence:\n"
        "```json manifest\n"
        '{"changed": "one-line summary", "files": ["path1"], "why": "…", '
        '"dependencies": ["what this relies on"], "needs_integration": ["what the '
        'integrator must reconcile"], "risks": ["…"], "do_not_create": ["files you '
        'considered and rejected"]}\n'
        "```"
    )


# --------------------------------------------------------------------------- #
# coordinator plan (runs before builders)                                      #
# --------------------------------------------------------------------------- #

def plan_task_text(db: Session, existing_files: list[str]) -> str:
    budget = max_repo_files(db)
    existing = ", ".join(existing_files[:40]) or "(empty)"
    return (
        "You are the COORDINATOR for this build. Do NOT write code. Produce the "
        "single integration plan every builder must follow.\n"
        f"Existing repo files: {existing}\n"
        f"Hard limit: at most {budget} files total; prefer far fewer.\n"
        "Return ONLY a JSON object in a ```json fence:\n"
        '{"files": [{"path": "relative/path.ext", "purpose": "one line", '
        '"owner_slot": 1}], "forbidden_files": ["paths/patterns that must NOT be '
        'created"], "entry_point": "main.py", "notes": "integration notes"}\n'
        "Each file has exactly ONE owner slot. Cover only what the project needs "
        "to run: entry point, core modules, README, dependency manifest."
    )


def parse_integration_plan(text: str) -> dict | None:
    m = _PLAN_FENCE.search(text)
    if not m:
        return None
    try:
        plan = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(plan, dict) or not isinstance(plan.get("files"), list):
        return None
    files = [f for f in plan["files"]
             if isinstance(f, dict) and isinstance(f.get("path"), str)]
    if not files:
        return None
    plan["files"] = files
    return plan


def plan_context_text(plan: dict, agent_slot: int | None = None) -> str:
    lines = ["INTEGRATION PLAN (binding — build ONLY what it assigns):"]
    for f in plan.get("files", [])[:40]:
        owner = f.get("owner_slot")
        marker = ""
        if agent_slot is not None and owner is not None:
            marker = "  ← YOUR FILE" if owner == agent_slot else "  (another agent's file — do not create)"
        lines.append(f"- {f['path']} — {f.get('purpose', '')}{marker}")
    if plan.get("entry_point"):
        lines.append(f"Entry point: {plan['entry_point']}")
    if plan.get("forbidden_files"):
        lines.append("Never create: " + ", ".join(str(x) for x in plan["forbidden_files"][:10]))
    if plan.get("notes"):
        lines.append(f"Notes: {plan['notes']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# agent manifest contract                                                      #
# --------------------------------------------------------------------------- #

def strip_manifest(text: str) -> str:
    """Remove the internal manifest block from anything user-facing."""
    return _MANIFEST_FENCE.sub("", text).rstrip() + "\n"


def parse_agent_manifest(text: str) -> dict | None:
    """The structured result block every agent owes (free text around it is
    material, not the deliverable)."""
    m = _MANIFEST_FENCE.search(text)
    if not m:
        return None
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return {k: data.get(k) for k in MANIFEST_KEYS if data.get(k) is not None}


# --------------------------------------------------------------------------- #
# deterministic integration pass                                               #
# --------------------------------------------------------------------------- #

def _repo_files(repo: Path) -> list[Path]:
    return [f for f in sorted(repo.rglob("*")) if f.is_file()]


def _referenced(repo: Path, target: Path, files: list[Path]) -> bool:
    """Is `target` mentioned (by name or module) anywhere else in the repo?"""
    stem = target.stem
    name = target.name
    for f in files:
        if f == target or f.suffix not in (".py", ".js", ".ts", ".md", ".json", ".html"):
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        if name in text or re.search(rf"\b(?:import|from)\s+[\w.]*\b{re.escape(stem)}\b", text):
            return True
    return False


def _entry_stub_paths(repo: Path) -> list[str]:
    from .build_integrity import _ENTRY_CANDIDATES, _is_stub_module
    real = [rel for rel in _ENTRY_CANDIDATES
            if (repo / rel).exists() and not _is_stub_module(repo / rel)]
    stubs = [rel for rel in _ENTRY_CANDIDATES
             if (repo / rel).exists() and _is_stub_module(repo / rel)]
    # a stub entry file is only junk when a real entry point exists
    return stubs if real else []


def integration_pass(db: Session, ws: Path) -> dict:
    """Deterministic final integration sweep over repo/.

    Removes what is unambiguously wrong (junk names, placeholder bodies, exact
    duplicate content, dead stub entry points) and REPORTS what needs judgment
    (same-name near-duplicates, file-budget overruns) so the LLM integrator —
    or a repair loop — resolves them instead of the client discovering them.
    """
    repo = ws / "repo"
    report: dict = {"removed": [], "kept": {}, "needs_review": [], "file_count": 0}
    if not repo.exists():
        return report

    files = _repo_files(repo)

    # 1. junk-named and placeholder files never ship
    for f in list(files):
        rel = str(f.relative_to(repo))
        try:
            junk = is_junk_filename(rel)
            placeholder = (f.stat().st_size <= 4096
                           and is_placeholder_content(f.read_text(errors="replace")))
        except (OSError, UnicodeDecodeError):
            continue
        if junk or placeholder:
            f.unlink()
            files.remove(f)
            report["removed"].append({"path": rel,
                                      "reason": "junk name" if junk else "placeholder body"})

    # 2. exact duplicate content → keep one canonical copy
    by_hash: dict[str, list[Path]] = {}
    for f in files:
        try:
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
        except OSError:
            continue
        by_hash.setdefault(digest, []).append(f)
    for paths in by_hash.values():
        if len(paths) < 2:
            continue
        # keep the copy other files actually reference; tie-break on path depth
        ranked = sorted(paths, key=lambda p: (not _referenced(repo, p, files),
                                              len(p.relative_to(repo).parts),
                                              str(p)))
        keep, drop = ranked[0], ranked[1:]
        for f in drop:
            rel = str(f.relative_to(repo))
            # same stem → imports resolve to the surviving canonical copy, so
            # deleting is safe; a differently-named referenced copy is a
            # judgment call for the integrator.
            if f.stem != keep.stem and _referenced(repo, f, files):
                report["needs_review"].append(
                    {"kind": "duplicate_content_referenced", "path": rel,
                     "duplicate_of": str(keep.relative_to(repo))})
                continue
            f.unlink()
            files.remove(f)
            report["removed"].append({"path": rel,
                                      "reason": f"identical to {keep.relative_to(repo)}"})
        report["kept"][str(keep.relative_to(repo))] = "canonical copy"

    # 3. dead stub entry points (a real entry point exists)
    for rel in _entry_stub_paths(repo):
        f = repo / rel
        if f in files and not _referenced(repo, f, files):
            f.unlink()
            files.remove(f)
            report["removed"].append({"path": rel, "reason": "stub entry point"})

    # 4. same-stem near-duplicates in different directories → judgment call
    by_stem: dict[str, list[Path]] = {}
    for f in files:
        if f.suffix in (".py", ".js", ".ts", ".tsx"):
            by_stem.setdefault(f.name, []).append(f)
    for name, paths in by_stem.items():
        if len(paths) > 1 and name not in ("__init__.py", "index.ts", "index.js"):
            report["needs_review"].append(
                {"kind": "same_name_in_multiple_dirs",
                 "paths": [str(p.relative_to(repo)) for p in paths]})

    # 5. file budget
    report["file_count"] = len(files)
    budget = max_repo_files(db)
    if len(files) > budget:
        report["needs_review"].append(
            {"kind": "file_budget_exceeded", "count": len(files), "budget": budget})

    return report


def apply_deletions(ws: Path, paths: list[str]) -> list[str]:
    """Apply the integrator's `=== DELETE: path ===` verdicts (repo-confined)."""
    repo = ws / "repo"
    removed: list[str] = []
    for rel in paths:
        target = (repo / rel).resolve()
        if not str(target).startswith(str(repo.resolve())):
            continue
        if target.is_file():
            target.unlink()
            removed.append(rel)
    return removed


def integrator_task_text(report: dict, manifests: list[dict]) -> str:
    """The instruction for the LLM integrator call — resolve exactly what the
    deterministic pass could not."""
    lines = [
        "You are the FINAL INTEGRATOR. The build agents finished; your job is to "
        "turn their material into ONE coherent, minimal project.",
        "Deterministic cleanup already ran. Resolve ONLY the items below:",
    ]
    for item in report.get("needs_review", [])[:10]:
        lines.append(f"- {json.dumps(item, ensure_ascii=False)}")
    if manifests:
        lines.append("\nAgent manifests (their declared integration needs):")
        for m in manifests[:8]:
            lines.append(f"- {json.dumps(m, ensure_ascii=False)[:400]}")
    lines.append(
        "\nActions available to you:\n"
        "* re-emit a merged/corrected file completely via `=== FILE: path ===` + fenced block;\n"
        "* remove a redundant file via a line `=== DELETE: path ===`;\n"
        "* fix imports/references in files you re-emit so the tree stays consistent.\n"
        "Keep ONE implementation per concern, unify naming, do not add features, "
        "do not create new files unless merging strictly requires it.")
    return "\n".join(lines)
