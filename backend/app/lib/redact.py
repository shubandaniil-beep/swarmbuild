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

_SECRET_NAME = re.compile(
    r"(?i)(api[_-]?key|secret(?:[_-]?key)?|access[_-]?key|auth[_-]?token|"
    r"client[_-]?secret|private[_-]?key|token|password|passwd|pwd)")

# Real assignment left-hand sides only. This deliberately anchors at the start
# of a statement so control flow like `if not API_KEY: return None`, imports and
# function calls are never treated as secret assignments.
_IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
_LHS = (
    rf"(?:{_IDENT})(?:\.{_IDENT})*"
    rf"|(?:os\.)?environ\[[^\]]+\]"
    rf"|process\.env\.{_IDENT}"
)
_LINE_ASSIGNMENT = re.compile(
    rf"^(?P<prefix>\s*(?:export\s+)?(?:(?:const|let|var)\s+)?"
    rf"(?P<lhs>{_LHS})(?:\s*:\s*[^=]+)?\s*=\s*)(?P<raw>.*)$")

# YAML / .env-style key-value entries at the start of a line. Inline dict/object
# entries with quoted keys are handled separately below.
_LINE_KEY_VALUE = re.compile(
    rf"^(?P<prefix>\s*(?P<key>{_IDENT}[\w-]*)\s*:\s*)(?P<raw>.*)$")
_QUOTED_KEY_VALUE = re.compile(
    r"(?P<prefix>(?P<key_quote>['\"])(?P<key>[^'\"]+)(?P=key_quote)\s*:\s*)"
    r"(?P<value_quote>['\"])(?P<value>(?:\\.|[^\\'\"])+)(?P=value_quote)")

# values that are obviously placeholders, not real secrets
_PLACEHOLDER_VALUE = re.compile(
    r"^(?:your[-_ ].*|change[-_ ]?me|replace[-_ ].*|example.*|placeholder.*|"
    r"x{3,}|<.*>|\.\.\.|\[REDACTED\]|test|dummy|none|null|true|false|\d+)$", re.I)

# Values that are CODE reading the secret from the environment/config, not the
# secret itself: `SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')`,
# `token = getenv("X")`, `key: process.env.API_KEY`. Redacting these mangles
# the expression (`[REDACTED]'FLASK_SECRET_KEY')`) and breaks the file's
# syntax while removing nothing sensitive.
_CODE_VALUE = re.compile(
    r"^(?:os\.|getenv\b|environ\b|process\.env|settings\.|config[.\[(]|"
    r"self\.|env[.\[(]|dotenv|secrets\.|load_)", re.I)


def _looks_like_code(value: str) -> bool:
    first = value.strip().split(None, 1)[0].rstrip(":;,") if value.strip() else ""
    if first in {"return", "if", "for", "while", "import", "from", "def", "class",
                 "lambda", "with", "try", "except", "raise", "yield", "await"}:
        return True
    if _CODE_VALUE.match(value):
        return True
    # unquoted expression fragments: function calls, indexing, f-strings,
    # env interpolation — never a literal secret value
    return any(tok in value for tok in ("(", ")", "[", "]", "{", "}", "${", "=>",
                                        "==", "!=", "=", " f'", ' f"', "f'", 'f"'))


def _secretish(name: str) -> bool:
    """True when a key/lhs name is semantically a secret holder."""
    if not name:
        return False
    bracket = re.search(r"\[['\"]([^'\"]+)['\"]\]", name)
    if bracket:
        name = bracket.group(1)
    else:
        name = name.rsplit(".", 1)[-1]
    return bool(_SECRET_NAME.search(name))


def _split_value(raw: str) -> tuple[str, str, str, str] | None:
    """Return (leading_ws, quote, value, suffix_after_value)."""
    leading = raw[:len(raw) - len(raw.lstrip())]
    body = raw.lstrip()
    if not body:
        return None
    quote = body[0] if body[0] in {"'", '"'} else ""
    if quote:
        escaped = False
        for i, ch in enumerate(body[1:], start=1):
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == quote:
                return leading, quote, body[1:i], body[i + 1:]
        return None
    comment_at = body.find("#")
    if comment_at >= 0:
        value_part, comment = body[:comment_at], body[comment_at:]
    else:
        value_part, comment = body, ""
    value = value_part.strip()
    suffix = value_part[len(value_part.rstrip()):] + comment
    return leading, "", value, suffix


def _safe_value_replacement(raw: str, found: set[str], label: str) -> str | None:
    parsed = _split_value(raw)
    if parsed is None:
        return None
    leading, quote, value, suffix = parsed
    if not value or len(value.strip()) < 6 or _PLACEHOLDER_VALUE.match(value):
        return None
    if not quote and _looks_like_code(value):
        return None
    found.add(label)
    return f"{leading}{quote}{PLACEHOLDER}{quote}{suffix}"


def _redact_quoted_key_values(text: str, found: set[str]) -> str:
    def repl(m: re.Match) -> str:
        key = m.group("key")
        if not _secretish(key):
            return m.group(0)
        value = m.group("value")
        if len(value.strip()) < 6 or _PLACEHOLDER_VALUE.match(value) or _looks_like_code(value):
            return m.group(0)
        found.add(f"assigned_{key.lower().replace('-', '_')}")
        return f"{m.group('prefix')}{m.group('value_quote')}{PLACEHOLDER}{m.group('value_quote')}"

    return _QUOTED_KEY_VALUE.sub(repl, text)


def _redact_assignments(text: str, found: set[str]) -> str:
    redacted_lines: list[str] = []
    for line in text.splitlines(keepends=True):
        ending = ""
        body = line
        if body.endswith("\r\n"):
            body, ending = body[:-2], "\r\n"
        elif body.endswith("\n"):
            body, ending = body[:-1], "\n"

        m = _LINE_ASSIGNMENT.match(body)
        if m and _secretish(m.group("lhs")):
            repl = _safe_value_replacement(
                m.group("raw"), found,
                f"assigned_{m.group('lhs').rsplit('.', 1)[-1].lower().replace('-', '_')}")
            if repl is not None:
                redacted_lines.append(f"{m.group('prefix')}{repl}{ending}")
                continue

        m = _LINE_KEY_VALUE.match(body)
        if m and _secretish(m.group("key")):
            repl = _safe_value_replacement(
                m.group("raw"), found,
                f"assigned_{m.group('key').lower().replace('-', '_')}")
            if repl is not None:
                redacted_lines.append(f"{m.group('prefix')}{repl}{ending}")
                continue

        redacted_lines.append(line)
    return "".join(redacted_lines)


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
    out = _redact_quoted_key_values(out, found)
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
