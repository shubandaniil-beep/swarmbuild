"""Micro-task build: one small model, many small verified steps.

When the usable pool degrades to a single cheap model (one route / one key),
asking it to emit a whole project in one shot reliably produces prose, partial
files or garbage. Instead the build sprint is decomposed:

    plan (file list as JSON) → generate one file → syntax-check → repair → next

Each step is a separate provider call with a narrow instruction, which is what
small models can actually do. The orchestrator consumes the returned results
through its normal loop, so budget caps, spend recording, honest progress
accounting and the release gates all apply unchanged.
"""
import ast
import json
import re
from pathlib import Path

from sqlalchemy.orm import Session

from .agent_runner import run_agent
from .settings_service import get_setting

_PLAN_FENCE = re.compile(r"```(?:json)?\s*\n(\[.*?\])\s*\n```", re.S)
_BARE_ARRAY = re.compile(r"(\[\s*\{.*?\}\s*\])", re.S)

_MAX_PLAN_FILES = 12

_PLAN_TASK = (
    "Do NOT write any code yet. Return ONLY a JSON array — the minimal list of "
    "files this project needs to run, most important first. Each item: "
    '{"path": "relative/path.ext", "purpose": "one line"}. '
    "Include an entry point (main.py or app.py), README.md and a dependency "
    f"manifest if needed. At most {_MAX_PLAN_FILES} files. "
    "Output the JSON array inside a ```json fence and nothing else."
)


def should_microtask(db: Session, assignments: list[dict]) -> bool:
    """True when the phase would otherwise hand the whole build to a single
    cheap real model — the case micro-tasking exists for."""
    if not bool(get_setting(db, "enable_micro_build")):
        return False
    cards = [a.get("card") or {} for a in assignments]
    if not cards:
        return False
    routes = {(c.get("provider_id"), c.get("model_name")) for c in cards}
    if len(routes) != 1:
        return False
    card = cards[0]
    if card.get("provider") == "mock":
        return False  # mock builds whole repos deterministically already
    return card.get("cost_level") in ("low", "free")


def _parse_plan(text: str) -> list[dict]:
    for pattern in (_PLAN_FENCE, _BARE_ARRAY):
        m = pattern.search(text)
        if not m:
            continue
        try:
            items = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(items, list):
            continue
        plan = []
        for item in items:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                plan.append({"path": item["path"].strip(),
                             "purpose": str(item.get("purpose", "")).strip()})
        if plan:
            return plan[:_MAX_PLAN_FILES]
    return []


def _file_task(entry: dict, done: list[str], brief_reminder: str) -> str:
    done_note = ("Files already written (do not repeat them): "
                 + ", ".join(done) + ". ") if done else ""
    return (
        f"Write EXACTLY ONE file now: `{entry['path']}` — {entry['purpose'] or 'part of the project'}. "
        f"{done_note}"
        "Emit the complete file via the FILE contract:\n\n"
        f"=== FILE: {entry['path']} ===\n```\n<complete file contents>\n```\n\n"
        "No other files, no prose before the marker. The file must be complete "
        f"and runnable, consistent with the project brief. {brief_reminder}"
    )


def _repair_task(path: str, error: str) -> str:
    return (
        f"The file `{path}` you just wrote does not parse: {error}. "
        f"Re-emit the corrected COMPLETE file via the FILE contract "
        f"(=== FILE: {path} === followed by a fenced block). Only that file."
    )


def _syntax_error(path: str, content: str) -> str | None:
    if not path.endswith(".py"):
        return None
    try:
        ast.parse(content)
        return None
    except (SyntaxError, ValueError) as e:
        return f"{e.__class__.__name__}: {e}"


def run_micro_build(db: Session, ws: Path, project, phase_key: str,
                    assignment: dict, agent_db_id: str,
                    budget_left_usd: float) -> list[tuple] | None:
    """Run the plan→file→check→repair loop with one worker assignment.

    Returns entries shaped exactly like the orchestrator's normal results —
    ``(assignment, agent_id, result, cost)`` — so the caller's existing loop
    applies files, records spend and enforces caps. Returns None when no plan
    could be obtained (caller falls back to the one-shot build).
    """
    from .event_log import log_event

    spent = 0.0
    entries: list[tuple] = []

    plan_result, cost = run_agent(db, ws, project, phase_key, assignment,
                                  agent_db_id, {"micro_task": _PLAN_TASK})
    spent += cost
    plan_result.files = {}  # the plan is coordination, never repo content
    entries.append((assignment, agent_db_id, plan_result, cost))
    plan = _parse_plan(plan_result.text)
    if not plan or getattr(plan_result, "status", "") == "mock_fallback":
        log_event(db, project.id, "micro_build_plan_failed",
                  "Микро-сборка: модель не вернула валидный план файлов — обычная сборка",
                  {"phase": phase_key}, ws)
        return None

    log_event(db, project.id, "micro_build_planned",
              f"Микро-сборка: план из {len(plan)} файлов",
              {"files": [p["path"] for p in plan]}, ws)

    brief_reminder = "Keep it minimal and working; no placeholders."
    done: list[str] = []
    for entry in plan:
        if budget_left_usd and spent >= budget_left_usd:
            log_event(db, project.id, "micro_build_capped",
                      "Микро-сборка остановлена по бюджету фазы",
                      {"spent_usd": round(spent, 6), "done": done}, ws)
            break
        result, cost = run_agent(db, ws, project, phase_key, assignment, agent_db_id,
                                 {"micro_task": _file_task(entry, done, brief_reminder)})
        spent += cost
        entries.append((assignment, agent_db_id, result, cost))
        if getattr(result, "status", "") == "mock_fallback":
            break  # provider is gone; do not fabricate the rest of the project

        content = result.files.get(entry["path"])
        if content is None and len(result.files) == 1:
            # model wrote the right file under a slightly different label
            content = next(iter(result.files.values()))
            result.files = {entry["path"]: content}
        if content is None:
            log_event(db, project.id, "micro_build_file_missing",
                      f"Микро-сборка: файл {entry['path']} не получен из ответа модели",
                      {"path": entry["path"]}, ws)
            continue

        error = _syntax_error(entry["path"], content)
        if error:
            fix, cost = run_agent(db, ws, project, phase_key, assignment, agent_db_id,
                                  {"micro_task": _repair_task(entry["path"], error)})
            spent += cost
            fixed = fix.files.get(entry["path"])
            if fixed is None and len(fix.files) == 1:
                fixed = next(iter(fix.files.values()))
                fix.files = {entry["path"]: fixed}
            if fixed is not None and not _syntax_error(entry["path"], fixed):
                entries.append((assignment, agent_db_id, fix, cost))
                done.append(entry["path"])
                continue
            # keep the broken original out of the repo: gates would fail anyway,
            # but an honest miss is better than shipping known-broken code
            fix.files = {}
            entries.append((assignment, agent_db_id, fix, cost))
            result.files.pop(entry["path"], None)
            log_event(db, project.id, "micro_build_file_broken",
                      f"Микро-сборка: {entry['path']} не прошёл проверку синтаксиса после repair",
                      {"path": entry["path"], "error": error}, ws)
            continue
        done.append(entry["path"])

    log_event(db, project.id, "micro_build_finished",
              f"Микро-сборка: {len(done)} файлов прошли проверку",
              {"done": done, "spent_usd": round(spent, 6)}, ws)
    return entries
