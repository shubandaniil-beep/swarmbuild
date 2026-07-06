"""Redacts internal platform/routing details that a model might echo back
into user-facing artifacts (system-prompt leakage, mandate/rotation talk).

This is a defense-in-depth net, not the primary control: prompts themselves
never describe the routing algorithm. This only strips accidental echoes.
"""
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

REDACTED = "[редактировано: внутренняя информация платформы]"  # verbatim prompt-line leak
REDACTED_SPAN = "[скрыто]"  # single leaked term inside otherwise-legit text

# Internal terms that reveal the routing/orchestration design and must never
# reach a user-facing artifact. Deliberately scoped to phrases that carry real
# leak value AND essentially never appear in legitimate deliverables — bare
# common words (packaging, intake, "system prompt", model_id, provider_id,
# "slot N", "allowed access") were removed because they shred normal business
# plans and generated code without protecting the algorithm. Phase-name mentions
# are only redacted when qualified with "phase:" / "phase " (a mention like a
# bare "packaging" phase leaks nothing — the UI already shows phase labels).
_INTERNAL_PATTERNS = [
    r"\bcurrent\s+mandate\s*:\s*(lead|critic|builder|reviewer|repairer|judge|packager)\b",
    r"\bmandate\s*:\s*(lead|critic|builder|reviewer|repairer|judge|packager)\b",
    r"\bphase\s*:\s*(intake|swarm_understanding|spec_war|architecture_battle|build_sprint|review_stop|repair_sprint|final_audit|packaging)\b",
    r"\bphase\s+(swarm_understanding|spec_war|architecture_battle|build_sprint|review_stop|repair_sprint|final_audit)\b",
    r"\b(swarm_understanding|spec_war|architecture_battle|build_sprint|review_stop|repair_sprint|build_rotation_plan|select_pool|swarm_state|agent_slot|prompt_path)\b",
    r"\bmock-swarm-[a-z0-9_-]+\b",
    r"\brotating ai swarm(?: platform)?\b",
    r"\bswarm review reports?\b",
    r"\brole[\s_-]?rotation\b",
    r"\bmodel[\s_-]?pool\b",
    r"\bphase[\s_-]?orchestrator\b",
    r"\bbudget[\s_-]?engine\b",
]
_INTERNAL_RE = re.compile("|".join(_INTERNAL_PATTERNS), re.IGNORECASE)


def _prompt_lines() -> list[str]:
    lines = []
    for f in PROMPTS_DIR.glob("*.md"):
        for line in f.read_text().splitlines():
            line = line.strip("-* \t")
            if len(line.split()) >= 6:
                lines.append(line.lower())
    return lines


_PROMPT_LINES = None


def _prompt_corpus() -> list[str]:
    global _PROMPT_LINES
    if _PROMPT_LINES is None:
        _PROMPT_LINES = _prompt_lines()
    return _PROMPT_LINES


def sanitize(text: str) -> tuple[str, int]:
    """Strip internal-platform echoes from agent-generated text.

    A whole line is dropped only when it reproduces a system-prompt sentence
    verbatim (a genuine IP leak). Otherwise a scattered internal term is masked
    inline, leaving the surrounding legitimate sentence/code intact.

    Returns (clean_text, redaction_count).
    """
    corpus = _prompt_corpus()
    out_lines = []
    hits = 0
    for line in text.splitlines():
        normalized = line.strip().lower()
        # 1) verbatim system-prompt sentence leaked → drop the whole line
        if len(normalized) > 20 and any(
                normalized == c or normalized in c for c in corpus):
            out_lines.append(REDACTED)
            hits += 1
            continue
        # 2) scattered internal term → mask just the term, keep the sentence
        new_line, n = _INTERNAL_RE.subn(REDACTED_SPAN, line)
        hits += n
        out_lines.append(new_line)
    return "\n".join(out_lines), hits
