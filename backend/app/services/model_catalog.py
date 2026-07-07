"""Provider model-catalog sync (Groq first).

The registry must not drift from what the provider actually serves: models get
deprecated, new production models appear, context windows change. This module
pulls the provider's live ``/models`` endpoint and reconciles the DB registry:

* live + known price → upserted and kept enabled;
* live but unpriced (typically preview) → registered but DISABLED, so a
  preview model never silently takes paid traffic until an admin prices it;
* in the DB but no longer served → disabled (deprecated), never deleted, so
  historical call logs keep resolving.

Prices are a curated table (the models endpoint does not return pricing);
non-chat models (whisper/tts/guard/embeddings) are skipped entirely.
"""
import json
import urllib.error
import urllib.request

from sqlalchemy.orm import Session

from ..models import ModelEntry, Provider
from ..providers.base import guarded_urlopen
from . import key_pool
from .settings_service import get_setting

# model id → (input $/1M, output $/1M, cost_level, production)
GROQ_PRICES: dict[str, tuple[float, float, str, bool]] = {
    "llama-3.3-70b-versatile": (0.59, 0.79, "medium", True),
    "llama-3.1-8b-instant": (0.05, 0.08, "low", True),
    "openai/gpt-oss-120b": (0.15, 0.60, "medium", True),
    "openai/gpt-oss-20b": (0.075, 0.30, "low", True),
    "meta-llama/llama-4-scout-17b-16e-instruct": (0.11, 0.34, "low", True),
    "meta-llama/llama-4-maverick-17b-128e-instruct": (0.20, 0.60, "medium", True),
    "qwen/qwen3-32b": (0.29, 0.59, "low", False),
    "moonshotai/kimi-k2-instruct": (1.00, 3.00, "medium", True),
    "deepseek-r1-distill-llama-70b": (0.75, 0.99, "medium", False),
    "gemma2-9b-it": (0.20, 0.20, "low", True),
}

# id substrings that are not chat-completion models
_NON_CHAT_MARKERS = ("whisper", "tts", "guard", "embed", "allam", "compound",
                     "moderation", "rerank")

_MAX_OUTPUT_CAP = 8192


def _is_chat_model(model_id: str) -> bool:
    low = model_id.lower()
    return not any(marker in low for marker in _NON_CHAT_MARKERS)


def fetch_provider_models(base_url: str, api_key: str, timeout: float = 15.0,
                          allow_private: bool = False) -> list[dict]:
    """GET {base_url}/models — OpenAI-compatible listing."""
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {api_key}",
                 "User-Agent": "SwarmBuild/1.0"})
    try:
        # guards the initial URL and every redirect hop (the API key rides this
        # request, so a redirect to an internal host must not be followed).
        with guarded_urlopen(req, timeout, allow_private) as resp:
            data = json.loads(resp.read(2_000_000))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"catalog fetch failed: HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"catalog fetch failed: {exc.reason}") from exc
    items = data.get("data") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise RuntimeError("catalog fetch failed: unexpected response shape")
    return [i for i in items if isinstance(i, dict) and i.get("id")]


def _display_name(model_id: str) -> str:
    tail = model_id.split("/")[-1].replace("-", " ").replace("_", " ")
    return f"Groq {tail.title()}"


def sync_groq_models(db: Session, provider: Provider) -> dict:
    """Reconcile the DB model registry with Groq's live catalog."""
    records = key_pool.ordered_key_records(db, provider)
    if not records:
        raise RuntimeError(f"{provider.name}: no usable API keys to query the catalog")
    live = fetch_provider_models(
        provider.base_url,
        records[0]["plaintext"],
        allow_private=bool(get_setting(db, "allow_private_provider_urls")),
    )

    existing = {m.model_name: m for m in
                db.query(ModelEntry).filter(ModelEntry.provider_id == provider.id).all()}
    live_ids: set[str] = set()
    added, updated, disabled, skipped = [], [], [], []

    for item in live:
        model_id = str(item["id"])
        if not _is_chat_model(model_id):
            skipped.append(model_id)
            continue
        live_ids.add(model_id)
        active = bool(item.get("active", True))
        context_window = int(item.get("context_window") or 0)
        max_completion = int(item.get("max_completion_tokens") or 0)
        max_out = min(max_completion or context_window or _MAX_OUTPUT_CAP, _MAX_OUTPUT_CAP)
        priced = GROQ_PRICES.get(model_id)

        entry = existing.get(model_id)
        if entry is None:
            context_tokens = context_window or 128000
            if priced:
                inp, outp, cost_level, production = priced
                db.add(ModelEntry(
                    display_name=_display_name(model_id), provider_id=provider.id,
                    model_name=model_id, cost_level=cost_level,
                    input_price_per_1m=inp, output_price_per_1m=outp,
                    supports_code=True, max_output_tokens=max_out,
                    max_context_tokens=context_tokens,
                    enabled=active and production,
                    priority=20 if production else 60,
                ))
                added.append(model_id)
            else:
                # unknown price (usually preview): visible to the admin, but a
                # model with no price must never take paid traffic silently
                db.add(ModelEntry(
                    display_name=_display_name(model_id) + " (unpriced)",
                    provider_id=provider.id, model_name=model_id,
                    cost_level="medium", input_price_per_1m=0,
                    output_price_per_1m=0, supports_code=True,
                    max_output_tokens=max_out, max_context_tokens=context_tokens,
                    enabled=False, priority=90,
                ))
                added.append(model_id)
            continue

        changed = False
        if priced:
            inp, outp, cost_level, production = priced
            if float(entry.input_price_per_1m) != inp or \
                    float(entry.output_price_per_1m) != outp:
                entry.input_price_per_1m = inp
                entry.output_price_per_1m = outp
                changed = True
            if entry.cost_level != cost_level:
                entry.cost_level = cost_level
                changed = True
        if max_out and entry.max_output_tokens != max_out:
            entry.max_output_tokens = max_out
            changed = True
        if not active and entry.enabled:
            entry.enabled = False  # provider marked it inactive
            changed = True
        if changed:
            updated.append(model_id)

    # models we track that the provider no longer serves → deprecated
    for model_id, entry in existing.items():
        if model_id not in live_ids and entry.enabled:
            entry.enabled = False
            entry.display_name = entry.display_name.replace(" (deprecated)", "") + " (deprecated)"
            disabled.append(model_id)

    db.commit()
    return {
        "provider": provider.name,
        "live_models": len(live_ids),
        "added": sorted(added),
        "updated": sorted(updated),
        "disabled_deprecated": sorted(disabled),
        "skipped_non_chat": sorted(skipped),
    }


def sync_provider_models(db: Session, provider: Provider) -> dict:
    if provider.provider_type == "groq":
        return sync_groq_models(db, provider)
    raise RuntimeError(f"catalog sync is not supported for provider type "
                       f"{provider.provider_type!r} yet")
