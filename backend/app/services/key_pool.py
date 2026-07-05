"""Provider key pool: rotate across many API keys of one operator.

A provider can hold a pool of keys (e.g. 15 Anthropic keys). The runner asks
this module for keys in least-recently-used order and fails over key-by-key,
so a single key hitting a rate limit doesn't stall the swarm. Plaintext keys
are only ever produced at call time via decrypt; they are never stored on cards.
"""
from datetime import datetime, timezone
import re

from sqlalchemy.orm import Session

from ..lib.crypto import decrypt_key, encrypt_key, mask_key
from ..models import Provider, ProviderKey


def _now() -> datetime:
    return datetime.now(timezone.utc)


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

    def sort_key(r: ProviderKey):
        errored = 1 if r.status == "error" else 0
        last = r.last_used_at or datetime.min.replace(tzinfo=timezone.utc)
        return (errored, r.use_count, last)

    rows.sort(key=sort_key)
    out: list[dict[str, str]] = []
    for r in rows:
        try:
            out.append({
                "id": r.id,
                "plaintext": decrypt_key(r.api_key_encrypted),
                "mask": r.api_key_mask,
                "status": r.status,
                "label": r.label,
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


_SPLIT = re.compile(r"[\s,;]+")


def is_key_scoped_error(message: str) -> bool:
    """Whether an upstream error should take this API key out of rotation."""
    text = (message or "").lower()
    return any(marker in text for marker in (
        "401",
        "403",
        "429",
        "unauthorized",
        "forbidden",
        "invalid api key",
        "invalid_api_key",
        "insufficient credits",
        "insufficient_credit",
        "quota",
        "rate limit",
        "rate_limit",
    ))


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
