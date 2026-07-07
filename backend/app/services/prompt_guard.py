"""Lightweight prompt-injection risk scanner for user briefs / uploaded text.

Flags attempts to subvert the swarm (exfiltrate secrets, read env, override
instructions, escalate privilege, run destructive commands). Tuned to catch
explicit attack phrasing without tripping on ordinary project requests.
"""
import re

# (category, weight, regex). Weight ≥ 2 => a single hit is enough for "medium".
_RULES: list[tuple[str, int, re.Pattern]] = [
    ("override_instructions", 2, re.compile(
        r"(?i)\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|"
        r"earlier|all)\b.{0,20}\b(instruction|prompt|rule|context)s?\b")),
    ("reveal_system_prompt", 3, re.compile(
        r"(?i)\b(reveal|show|print|repeat|leak|expose|output)\b.{0,30}"
        r"\b(system|hidden|internal|developer)\b.{0,10}\bprompt\b")),
    ("exfiltrate_secrets", 3, re.compile(
        r"(?i)\b(print|reveal|show|leak|send|expose|dump|list|exfiltrate|steal|"
        r"extract|scrape|obtain)\b.{0,30}"
        # object: generic secret words, OR the concrete high-signal names this
        # deployment actually holds (ENCRYPTION_SECRET is one _word_, so a bare
        # `\bsecret` never matches it — spell the env names out).
        r"(?:\b(secret|api[\s_-]?key|password|token|credential)s?\b|"
        r"ENCRYPTION_SECRET|SECRET_KEY|\.env\b)")),
    ("read_env", 3, re.compile(
        r"(?i)(environment variables?|os\.environ|process\.env|printenv|\bgetenv\b|"
        r"read\b.{0,15}\b\.env\b)")),
    ("exfiltrate_to_url", 2, re.compile(
        r"(?i)\b(send|post|upload|exfiltrate|leak|forward)\b.{0,40}"
        r"\b(https?://|external (?:url|server|endpoint)|webhook)\b")),
    ("destructive_command", 2, re.compile(
        r"(?i)(rm\s+-rf|drop\s+(?:table|database)|del\s+/|format\s+c:|"
        r"shutdown|:\(\)\s*\{)")),
    ("disable_safety", 3, re.compile(
        r"(?i)\b(disable|turn off|bypass|ignore|remove)\b.{0,20}"
        r"\b(safety|guardrail|filter|moderation|restriction)s?\b")),
    ("privilege_escalation", 2, re.compile(
        r"(?i)\b(act as|you are now|pretend to be|become)\b.{0,15}\b(admin|root|"
        r"administrator|superuser|developer mode)\b")),
    ("bypass_access_control", 3, re.compile(
        r"(?i)\b(bypass|disable|skip|circumvent)\b.{0,20}"
        r"\b(access control|authorization|authentication|permission|ownership)s?\b")),
    ("jailbreak", 2, re.compile(
        r"(?i)\b(jailbreak|DAN mode|do anything now)\b"
        r"|(?:you are now|act as|pretend to be|enter)\s+DAN\b")),
]


def scan(text: str) -> dict:
    """Return {risk_level, score, categories}. risk_level in low|medium|high."""
    if not text:
        return {"risk_level": "low", "score": 0, "categories": []}
    score = 0
    categories: list[str] = []
    for category, weight, rx in _RULES:
        if rx.search(text):
            score += weight
            categories.append(category)
    if score >= 5 or len(categories) >= 3:
        level = "high"
    elif score >= 2:
        level = "medium"
    else:
        level = "low"
    return {"risk_level": level, "score": score, "categories": sorted(set(categories))}
