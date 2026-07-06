"""Provider key pool: rotate across many API keys of one operator.

A provider can hold a pool of keys (e.g. 15 Anthropic keys). The runner asks
this module for keys in least-recently-used order and fails over key-by-key,
so a single key hitting a rate limit doesn't stall the swarm. Plaintext keys
are only ever produced at call time via decrypt; they are never stored on cards.
"""
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from ..lib.crypto import decrypt_key, encrypt_key, mask_key
from ..models import Provider, ProviderKey


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes even for timezone=True columns."""
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


def is_cooling(record_or_row, now: datetime | None = None) -> bool:
    until = record_or_row.get("cooldown_until") if isinstance(record_or_row, dict) \
        else getattr(record_or_row, "cooldown_until", None)
    until = _aware(until)
    return bool(until and until > (now or _now()))


def usable_key_count(db: Session, provider: Provider) -> int:
    """Keys the runner is allowed to use for normal project work.

    Explicit provider tests may retry errored keys, but project routing only
    treats enabled non-error keys as usable. That keeps the runtime honest:
    a provider with only broken keys is not considered ready.
    """
    rows = _rows(db, provider)
    return sum(1 for r in rows if r.enabled and r.api_key_encrypted and r.status != "error")


def has_usable_key(db: Session, provider: Provider) -> bool:
    return usable_key_count(db, provider) > 0


def has_any_key(db: Session, provider: Provider) -> bool:
    """Backward-compatible alias for older call sites."""
    return has_usable_key(db, provider)


def _rows(db: Session, provider: Provider) -> list[ProviderKey]:
    """Pool rows for a provider, lazily migrating a legacy single key in."""
    rows = (db.query(ProviderKey)
            .filter(ProviderKey.provider_id == provider.id).all())
    if not rows and provider.api_key_encrypted:
        pk = ProviderKey(provider_id=provider.id,
                         api_key_encrypted=provider.api_key_encrypted,
                         api_key_mask=provider.api_key_mask,
                         label="legacy", status=provider.status)
        db.add(pk)
        db.commit()
        rows = [pk]
    return rows


def ordered_key_records(db: Session, provider: Provider,
                        include_errored: bool = False) -> list[dict[str, str]]:
    """Enabled keys as records, least-recently-used first.

    Healthy keys come before errored ones; within each group, lowest use_count
    and oldest last_used win, so load spreads evenly across the pool.
    """
    rows = [r for r in _rows(db, provider)
            if r.enabled and r.api_key_encrypted and (include_errored or r.status != "error")]
    now = _now()

    def sort_key(r: ProviderKey):
        errored = 1 if r.status == "error" else 0
        cooling = 1 if is_cooling(r, now) else 0
        last = _aware(r.last_used_at) or datetime.min.replace(tzinfo=UTC)
        return (errored, cooling, r.use_count, last)

    rows.sort(key=sort_key)
    out: list[dict] = []
    for r in rows:
        try:
            out.append({
                "id": r.id,
                "plaintext": decrypt_key(r.api_key_encrypted),
                "mask": r.api_key_mask,
                "status": r.status,
                "label": r.label,
                "cooldown_until": _aware(r.cooldown_until),
            })
        except Exception:
            continue
    return out


def ordered_keys(db: Session, provider: Provider,
                 include_errored: bool = False) -> list[tuple[str, str]]:
    """Compatibility wrapper returning (key_id, plaintext)."""
    return [(r["id"], r["plaintext"])
            for r in ordered_key_records(db, provider, include_errored)]


def mark_ok(db: Session, key_id: str) -> None:
    pk = db.get(ProviderKey, key_id)
    if not pk:
        return
    pk.status = "active"
    pk.last_error = ""
    pk.cooldown_until = None
    pk.use_count += 1
    pk.last_used_at = _now()
    db.commit()


def mark_error(db: Session, key_id: str, err: str) -> None:
    pk = db.get(ProviderKey, key_id)
    if not pk:
        return
    pk.status = "error"
    pk.last_error = err[:300]  # adapters never echo the key itself
    pk.last_used_at = _now()
    db.commit()


def mark_cooldown(db: Session, key_id: str, err: str, seconds: float) -> None:
    """Take a rate-limited key out of rotation temporarily. It recovers on its
    own once the window passes — a 429 must never brick a key permanently."""
    pk = db.get(ProviderKey, key_id)
    if not pk:
        return
    pk.last_error = err[:300]
    pk.last_used_at = _now()
    pk.cooldown_until = _now() + timedelta(seconds=max(1.0, seconds))
    db.commit()


_SPLIT = re.compile(r"[\s,;]+")

_PERMANENT_MARKERS = (
    "401",
    "403",
    "unauthorized",
    "forbidden",
    "invalid api key",
    "invalid_api_key",
    "api key not valid",
    "incorrect api key",
    "insufficient credits",
    "insufficient_credit",
)

# Rate-limit / quota windows: the key works, but this moment is throttled.
_RATE_LIMIT_MARKERS = (
    "429",
    "too many requests",
    "rate limit",
    "rate_limit",
    "quota",
    "resourceexhausted",
    "resource_exhausted",
    "overloaded",
    "529",
)

# Upstream server faults and network blips: nothing wrong with the key or the
# request — the provider (or the connection) hiccuped and a retry commonly
# succeeds. A Gemini "model overloaded" reply, for instance, is an HTTP 503 with
# an empty body, so only the status code identifies it (see _TRANSIENT_HTTP_5XX).
_SERVER_FAULT_MARKERS = (
    "unavailable",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "timed out",
    "timeout",
    "temporarily",
    "connection error",
    "connection reset",
    "connection aborted",
    "deadline",  # read_json_with_deadline: "provider response exceeded Ns deadline"
)

# Matches the adapter's "provider HTTP 5xx: ..." message for any 500-599 status.
_TRANSIENT_HTTP_5XX = re.compile(r"http\s*5\d\d")


def is_permanent_key_error(message: str) -> bool:
    """Errors a retry cannot heal: bad/revoked key, no balance. These take the
    key out of rotation until an admin retests it."""
    text = (message or "").lower()
    return any(marker in text for marker in _PERMANENT_MARKERS)


def is_transient_server_error(message: str) -> bool:
    """A transient upstream/network fault (5xx, gateway, timeout, connection,
    response deadline) — as opposed to a rate limit. The runner uses a short
    backoff for these instead of parking the key for a full rate-limit window."""
    text = (message or "").lower()
    if _TRANSIENT_HTTP_5XX.search(text):
        return True
    return any(marker in text for marker in _SERVER_FAULT_MARKERS)


def is_transient_key_error(message: str) -> bool:
    """Retryable, self-healing conditions: rate-limit/quota windows *and*
    transient server or network faults. The key stays in the pool; the runner
    waits briefly and retries rather than failing the phase on a passing blip."""
    text = (message or "").lower()
    if any(marker in text for marker in _RATE_LIMIT_MARKERS):
        return True
    return is_transient_server_error(text)


def is_key_scoped_error(message: str) -> bool:
    """Backward-compatible: whether the error is about this key at all."""
    return is_permanent_key_error(message) or is_transient_key_error(message)


def add_keys(db: Session, provider: Provider, raw: str, label_prefix: str = "") -> int:
    """Bulk-add keys from a pasted blob (newline/comma/space separated).

    De-duplicates on the actual key value (masks are lossy and collide on keys
    that share a prefix/suffix, as real API keys do). Returns count added.
    """
    candidates = [k.strip() for k in _SPLIT.split(raw or "") if k.strip()]
    existing = set()
    for r in _rows(db, provider):
        try:
            existing.add(decrypt_key(r.api_key_encrypted))
        except Exception:
            continue
    start = db.query(ProviderKey).filter(ProviderKey.provider_id == provider.id).count()
    added = 0
    for key in candidates:
        if key in existing:
            continue
        existing.add(key)
        label = f"{label_prefix}{start + added + 1}" if label_prefix else ""
        db.add(ProviderKey(provider_id=provider.id, label=label,
                           api_key_encrypted=encrypt_key(key), api_key_mask=mask_key(key)))
        added += 1
    if added:
        db.commit()
    return added
