"""UI recipe retrieval.

Picks the 1-2 most relevant UI recipes from app/ui_library for a given project
brief and injects ONLY those into the builder/integrator prompt — so the weak-UI
model composes from vetted patterns instead of inventing layout from scratch, and
we never blow the token budget by loading the whole library.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_LIB = Path(__file__).resolve().parent.parent / "ui_library"
_INDEX = _LIB / "index.json"
_RECIPES = _LIB / "recipes"

# Hard cap on the injected UI block. base_agent+builder (~1.3k tok) + brief must
# leave the whole builder input under 3000 tokens, so the recipe block stays <=1500.
UI_TOKEN_BUDGET = 1500

# Mandates that actually emit UI. Others (backend, docs) skip retrieval.
UI_MANDATES = {"builder", "integrator", "repairer"}
# Project types (as emitted by auto_detect) that have a visual web frontend.
# NB: code_project is the generic-code fallback (scripts, APIs, libraries, CLIs) —
# usually no frontend, so it is deliberately excluded to avoid injecting UI recipes
# into backend/CLI builds. Real web work routes to web_app/landing_page/dashboard.
UI_PROJECT_TYPES = {
    "web_app", "landing_page", "dashboard",
}

# Explicit color words boost matching color-tagged recipes.
_COLOR_WORDS = {
    "green": "green", "зелен": "green", "sage": "green",
    "dark": "dark", "тёмн": "dark", "темн": "dark", "black": "dark", "night": "dark",
    "blue": "blue", "син": "blue", "голуб": "blue",
    "violet": "violet", "purple": "violet", "фиолет": "violet",
    "warm": "warm", "тёпл": "warm", "тепл": "warm", "terracotta": "warm",
    "cream": "warm", "amber": "warm", "beige": "warm",
    "pastel": "pastel", "neon": "neon", "mono": "monochrome", "minimal": "minimal",
}

# Frontend framework requested in the brief → tell the builder to port the (HTML)
# recipes into that framework. The swarm emits static HTML by default, so this only
# fires when the client explicitly asks for a framework.
_FRAMEWORK_WORDS = {
    "react": "React", "реакт": "React", "next": "Next.js", "некст": "Next.js",
    "nextjs": "Next.js", "jsx": "React", "vite": "React (Vite)",
    "vue": "Vue", "вью": "Vue", "svelte": "Svelte", "свелт": "Svelte",
}


@lru_cache(maxsize=1)
def _load_index() -> list[dict]:
    if not _INDEX.exists():
        return []
    return json.loads(_INDEX.read_text()).get("recipes", [])


def _norm(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zа-я0-9]+", _norm(text)))


def _hits(terms, brief_norm: str, brief_tokens: set[str]) -> int:
    """Count matching terms. Terms >=3 chars match as a substring (tolerant of RU
    inflection: `бар` hits `бара`); shorter terms must match a whole token, so a
    2-letter term like `ии`/`ai` can't fire inside `конференции`/`retail`."""
    n = 0
    for t in terms:
        if not t:
            continue
        if len(t) >= 3:
            n += t in brief_norm
        else:
            n += t in brief_tokens
    return n


def _score(recipe: dict, brief_norm: str, brief_tokens: set[str],
           forced_colors: set[str]) -> float:
    # keyword hits from the brief (substring → tolerant of RU inflection)
    score = float(_hits(recipe.get("keywords", []), brief_norm, brief_tokens))
    # domain hits count double — matching "restaurant"/"shop" matters most
    score += 2.0 * _hits(recipe.get("domain", []), brief_norm, brief_tokens)
    # explicit color request is a strong signal
    if forced_colors and set(recipe.get("colors", [])) & forced_colors:
        score += 3.0
    return score


def _is_page(entry: dict) -> bool:
    return entry.get("kind", "page") == "page"


def select_recipes(brief: str, project_type: str, mandate: str,
                   max_recipes: int = 2, min_score: float = 2.0) -> list[dict]:
    """Return the top matching PAGE recipes (may be empty)."""
    if mandate not in UI_MANDATES or project_type not in UI_PROJECT_TYPES:
        return []
    index = [e for e in _load_index() if _is_page(e)]
    if not index:
        return []
    brief_norm = _norm(brief)
    brief_tokens = _tokens(brief)
    forced_colors = {c for w, c in _COLOR_WORDS.items() if w in brief_norm}
    ranked = sorted(
        ((_score(r, brief_norm, brief_tokens, forced_colors), r) for r in index),
        key=lambda t: t[0], reverse=True,
    )
    picked = [r for s, r in ranked if s >= min_score][:max_recipes]
    return picked


def select_components(brief: str, max_components: int = 3) -> list[dict]:
    """Return interactive component recipes whose triggers appear in the brief."""
    brief_norm = _norm(brief)
    brief_tokens = _tokens(brief)
    comps = [e for e in _load_index() if not _is_page(e)]
    ranked = []
    for c in comps:
        hits = _hits(c.get("triggers", []), brief_norm, brief_tokens)
        if hits:
            ranked.append((hits, c))
    ranked.sort(key=lambda t: t[0], reverse=True)
    return [c for _, c in ranked][:max_components]


def _detect_framework(brief_norm: str, brief_tokens: set[str]) -> str | None:
    for word, name in _FRAMEWORK_WORDS.items():
        if (word in brief_tokens) if len(word) <= 3 else (word in brief_norm):
            return name
    return None


def recipe_body(file_name: str) -> str:
    """Recipe markdown with its frontmatter stripped (the frontmatter is index-only).

    `file_name` is relative to the ui_library root, e.g. ``recipes/x.md`` or
    ``components/y.md`` (older ``x.md`` names resolve under recipes/ for safety).
    """
    path = _LIB / file_name
    if not path.exists():
        path = _LIB / "recipes" / file_name
    if not path.exists():
        return ""
    text = path.read_text()
    return re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL).strip()


def est_tokens(text: str) -> int:
    """Conservative token estimate (code + Cyrillic tokenize densely: ~3 chars/token)."""
    return len(text) // 3


def build_ui_context(brief: str, project_type: str, mandate: str,
                     token_budget: int = UI_TOKEN_BUDGET) -> str:
    """Injectable UI block, capped at token_budget. '' if nothing relevant matched.

    Recipes are added top-match first and only while the running block stays within
    budget — so the builder's total input never crosses the 3000-token ceiling.
    """
    picks = select_recipes(brief, project_type, mandate)
    if not picks:
        return ""
    header = (
        "## UI REFERENCE LIBRARY (use these — do not invent layout from scratch)\n"
        "You have vetted, on-brand UI recipes below. Pick the closest page recipe, then "
        "adapt its palette, copy and components to THIS project. Follow each recipe's "
        "own 'Adaptation rules'. Reuse the design tokens and component structure; "
        "change the content, not the craft. Any <component> blocks are drop-in "
        "interactive pieces — use them where the project needs that behavior.\n\n"
        "### CRITICAL — ship FINISHED content, never a template\n"
        "Deliver a fully rendered page with REAL content invented for THIS client from "
        "the brief: a concrete brand/product name, a real headline and subcopy, real "
        "numbers, real feature and section text. Write out every repeated block as "
        "actual markup — e.g. three real feature cards, four real stat figures. "
        "DO NOT output templating placeholders (`{{ variable }}`, `{% for %}`, "
        "`{% if %}`, `${...}`, `<!-- TODO -->`) or empty loops: a human opening the "
        "file must see a complete site, not variable names. If the brief omits a "
        "detail, invent a plausible concrete value rather than leaving a placeholder."
    )
    parts = [header]
    used = est_tokens(header)

    def _admit(entry: dict, tag: str, force: bool) -> bool:
        nonlocal used
        body = recipe_body(entry["file"])
        if not body:
            return False
        block = f"\n<{tag} id=\"{entry['id']}\">\n{body}\n</{tag}>"
        cost = est_tokens(block)
        if not force and used + cost > token_budget:
            return False
        parts.append(block)
        used += cost
        return True

    # one page recipe is the backbone (always admitted, even if oversized)
    _admit(picks[0], "recipe", force=True)
    # then interactive components the brief calls for, while budget allows
    for comp in select_components(brief):
        _admit(comp, "component", force=False)

    # framework port directive — only when the client asked for one
    fw = _detect_framework(_norm(brief), _tokens(brief))
    if fw:
        parts.append(
            f"\n## FRAMEWORK: {fw}\nThe recipes above are HTML/Tailwind. Port them to "
            f"{fw}: split the layout into function components, keep the exact Tailwind "
            f"classes, and implement any interactive <component> with the framework's "
            f"state (e.g. hooks) instead of vanilla JS. Keep the visual result identical."
        )
    return "\n".join(parts)
