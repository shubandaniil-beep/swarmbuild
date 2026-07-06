"""Swarm Personality Modes — a selectable "build style" that steers agent
decisions (stack complexity, feature scope, docs, security, tone, creativity).

This lives entirely in the prompt layer: a directive is appended to each agent's
instructions. It does NOT touch model routing/rotation — only how agents think
about the deliverable — so it carries no algorithm-leak risk.
"""

DEFAULT_MODE = "balanced"

# key -> {display_name, hint (user-facing, RU), directive (fed to agents, EN)}
MODES: dict[str, dict] = {
    "balanced": {
        "display_name": "Balanced",
        "hint": "сбалансированно по умолчанию",
        "directive": ("Balanced build style: reasonable scope, a standard mainstream "
                      "stack, and adequate documentation. No extremes."),
    },
    "conservative_build": {
        "display_name": "Conservative Build",
        "hint": "проверенные решения, минимум рисков",
        "directive": ("Conservative build style: favor proven, low-risk, well-documented "
                      "technologies. Avoid experimental dependencies. Prioritize stability "
                      "and long-term maintainability over novelty or cleverness."),
    },
    "startup_aggressive": {
        "display_name": "Startup Aggressive",
        "hint": "скорость и рост, фичи важнее полировки",
        "directive": ("Startup-aggressive build style: optimize for speed to market and "
                      "growth. Ship the boldest genuinely useful feature set quickly. "
                      "Accept reasonable, clearly-noted tech debt; momentum over polish."),
    },
    "cheap_mvp": {
        "display_name": "Cheap MVP",
        "hint": "минимальный стек, меньше фич",
        "directive": ("Cheap-MVP build style: minimize cost and complexity. Use the "
                      "simplest possible stack with the fewest dependencies, and include "
                      "only the core features that prove the idea. Cut everything "
                      "non-essential and say what was cut."),
    },
    "enterprise_clean": {
        "display_name": "Enterprise Clean",
        "hint": "документация, безопасность, надёжность",
        "directive": ("Enterprise-clean build style: enterprise-grade rigor. Thorough "
                      "documentation, explicit security considerations (authentication, "
                      "input validation, secrets handling), robust error handling, and "
                      "testing notes. Clean, conventional, well-layered architecture."),
    },
    "creative_chaos": {
        "display_name": "Creative Chaos",
        "hint": "нестандартные идеи и подходы",
        "directive": ("Creative-chaos build style: be inventive and unconventional. "
                      "Propose unexpected features, novel angles, and bold solutions. "
                      "Favor originality — but keep the result actually buildable."),
    },
    "academic_formal": {
        "display_name": "Academic Formal",
        "hint": "формально, структурировано, со ссылками",
        "directive": ("Academic-formal build style: precise, structured, methodical. Use "
                      "clear definitions, rigorous reasoning, formal structure, and "
                      "references/citations where relevant. Avoid casual phrasing."),
    },
}


def normalize(mode: str | None) -> str:
    return mode if mode in MODES else DEFAULT_MODE


def directive_for(mode: str | None) -> str:
    return MODES[normalize(mode)]["directive"]


def list_public() -> list[dict]:
    """Modes for the UI — display name + hint only (directives stay internal)."""
    return [{"key": k, "display_name": v["display_name"], "hint": v["hint"]}
            for k, v in MODES.items()]
