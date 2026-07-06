"""Secret redaction engine — one place that knows what a secret looks like.

Used for (a) scrubbing logs/errors/model outputs so keys never get persisted,
and (b) scanning generated artifacts before packaging. High-signal shapes only,
so normal prose and placeholder .env values are not flagged.
"""
import re

PLACEHOLDER = "[REDACTED]"

# (label, regex) for concrete secret shapes.
_SECRET_RULES: list[tuple[str, re.Pattern]] = [
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai_key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9]{20,}")),
    ("google_gemini_key", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("telegram_bot_token", re.compile(r"\b\d{6,10}:[A-Za-z0-9_\-]{30,}\b")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{6,}")),
    ("private_key", re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----[\s\S]*?"
        r"-----END (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("db_url_with_password", re.compile(
        r"\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp)://"
        r"[^:\s/@]+:[^@\s/]+@[^\s]+")),
]

# `KEY = value` style secrets, e.g. API_KEY=..., SECRET=..., PASSWORD=...
_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|secret(?:[_-]?key)?|access[_-]?key|auth[_-]?token|"
    r"client[_-]?secret|private[_-]?key|token|password|passwd|pwd)\b"
    r"(\s*[:=]\s*)(['\"]?)([^\s'\"#]{6,})(\3)")

# values that are obviously placeholders, not real secrets
_PLACEHOLDER_VALUE = re.compile(
    r"^(?:your[-_ ].*|change[-_ ]?me|replace[-_ ].*|example.*|placeholder.*|"
    r"x{3,}|<.*>|\.\.\.|test|dummy|none|null|true|false|\d+)$", re.I)


def _redact_assignments(text: str, found: set[str]) -> str:
    def repl(m: re.Match) -> str:
        value = m.group(4)
        if _PLACEHOLDER_VALUE.match(value):
            return m.group(0)  # placeholder — leave it
        found.add(f"assigned_{m.group(1).lower().replace('-', '_')}")
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{PLACEHOLDER}{m.group(5)}"

    return _ASSIGNMENT.sub(repl, text)


def redact(text: str) -> tuple[str, list[str]]:
    """Return (redacted_text, sorted list of secret labels found)."""
    if not text:
        return text, []
    found: set[str] = set()
    out = text
    for label, rx in _SECRET_RULES:
        if rx.search(out):
            found.add(label)
            out = rx.sub(PLACEHOLDER, out)
    out = _redact_assignments(out, found)
    return out, sorted(found)


def scan(text: str) -> list[str]:
    """Labels of any secrets present, without modifying the text."""
    return redact(text)[1]


def redact_text(text: str) -> str:
    return redact(text)[0]


def redact_error(exc: BaseException) -> str:
    """Safe string form of an exception with any embedded secret scrubbed."""
    return redact_text(str(exc))
