"""Model Pool Service — DB-backed model registry (spec-2 §4).

Models and providers live in the database and are managed from the admin
panel. Env vars are only the initial seed. Any enabled model can take any
mandate — rotation stays mandatory.
"""
from sqlalchemy.orm import Session

from ..models import ModelEntry, Provider
from .settings_service import get_setting

ALL_MANDATES = ["lead", "critic", "builder", "reviewer", "repairer", "judge", "packager"]

# legacy fallback used only when the registry is empty/unavailable
FALLBACK_MOCK_CARDS = [
    {"id": "mock_fast", "provider": "mock", "provider_id": None, "model_name": "mock-swarm-v1",
     "cost_level": "free", "input_cost_per_1m": 0.01, "output_cost_per_1m": 0.02,
     "max_output_tokens": 8000, "default_temperature": 0.0, "base_url": ""},
    {"id": "mock_cheap", "provider": "mock", "provider_id": None, "model_name": "mock-swarm-mini",
     "cost_level": "free", "input_cost_per_1m": 0.005, "output_cost_per_1m": 0.01,
     "max_output_tokens": 4000, "default_temperature": 0.0, "base_url": ""},
]


def _card(entry: ModelEntry, provider: Provider) -> dict:
    return {
        "id": entry.id,
        "display_name": entry.display_name,
        "provider": provider.provider_type,
        "provider_id": provider.id,
        "base_url": provider.base_url,
        "model_name": entry.model_name,
        "cost_level": entry.cost_level,
        "input_cost_per_1m": float(entry.input_price_per_1m),
        "output_cost_per_1m": float(entry.output_price_per_1m),
        "max_output_tokens": entry.max_output_tokens,
        "default_temperature": 0.3,
        "supports_code": entry.supports_code,
        "supports_json": entry.supports_json,
        "priority": entry.priority,
        "provider_priority": provider.priority,
        "provider_status": provider.status,
    }


def _runtime_card(db: Session, entry: ModelEntry, provider: Provider) -> dict:
    card = _card(entry, provider)
    token_cap = int(get_setting(db, "provider_max_output_tokens") or 0)
    if token_cap > 0:
        card["max_output_tokens"] = min(int(card.get("max_output_tokens") or token_cap), token_cap)
    timeout = int(get_setting(db, "provider_call_timeout_seconds") or 0)
    if timeout > 0:
        card["timeout_seconds"] = timeout
    if provider.provider_type == "openrouter":
        card["http_referer"] = str(get_setting(db, "openrouter_http_referer") or "").strip()
        card["app_title"] = str(get_setting(db, "openrouter_app_title") or "").strip()
    return card


def available_cards(db: Session, saving_mode: bool = False) -> list[dict]:
    from .key_pool import has_usable_key

    real_calls = bool(get_setting(db, "enable_real_model_calls"))
    mock_mode = bool(get_setting(db, "enable_mock_mode"))
    default_provider = str(get_setting(db, "default_provider") or "auto").strip().lower()
    default_model = str(get_setting(db, "default_model") or "").strip()
    rows = (db.query(ModelEntry, Provider)
            .join(Provider, ModelEntry.provider_id == Provider.id)
            .filter(ModelEntry.enabled.is_(True), Provider.enabled.is_(True))
            .order_by(ModelEntry.priority.asc(), ModelEntry.display_name.asc())
            .all())
    real_cards = []
    mock_cards = []
    real_configured = False
    for entry, provider in rows:
        if provider.provider_type == "mock":
            if mock_mode:
                mock_cards.append(_runtime_card(db, entry, provider))
            continue
        real_configured = True
        if real_calls and has_usable_key(db, provider):
            real_cards.append(_runtime_card(db, entry, provider))

    # Admin settings can pin a real provider/model, but stale legacy mock pins
    # are ignored whenever a real usable pool exists.
    if default_provider not in ("", "auto", "mock"):
        pinned = [c for c in real_cards if c["provider"] == default_provider]
        real_cards = pinned or real_cards
    if default_model and default_model not in {"mock-swarm-v1", "mock-swarm-mini"}:
        pinned = [c for c in real_cards if c["model_name"] == default_model]
        real_cards = pinned or real_cards

    real_cards.sort(key=lambda c: (
        0 if c.get("provider_status") == "active" else 1,
        c.get("provider_priority", 100),
        c.get("priority", 100),
        c.get("display_name") or c.get("model_name") or "",
    ))
    if real_cards:
        cards = real_cards
        if saving_mode:
            cheap = [c for c in cards if c["cost_level"] in ("low", "free")]
            cards = cheap or cards
        return cards
    if real_calls and real_configured:
        raise RuntimeError("real model calls are enabled, but no usable real API keys are available")
    if mock_mode:
        cards = mock_cards or [dict(c) for c in FALLBACK_MOCK_CARDS]
        if saving_mode:
            cheap = [c for c in cards if c["cost_level"] in ("low", "free")]
            cards = cheap or cards
        return cards
    raise RuntimeError("no enabled real model with usable API keys is configured")


def select_pool(db: Session, swarm_size: int, saving_mode: bool = False) -> list[dict]:
    """Return `swarm_size` cards, cycling the available registry.

    Duplicated models become distinct virtual agents so rotation happens even
    with a single available model.
    """
    available = available_cards(db, saving_mode)
    pool = []
    for i in range(swarm_size):
        card = dict(available[i % len(available)])
        if i >= len(available):
            card["id"] = f"{card['id']}_v{i // len(available) + 1}"
        pool.append(card)
    return pool


def alternative_card(db: Session, failed_card: dict) -> dict | None:
    """Failover step 2 (spec-2 §13): another model of the same cost level."""
    cards = alternative_cards(db, failed_card)
    return cards[0] if cards else None


def alternative_cards(db: Session, failed_card: dict) -> list[dict]:
    """Same-cost alternatives, excluding the same provider/model route.

    Virtual swarm cards get ids like `<model_id>_v2`, so id comparison is not
    enough: failover must avoid retrying the same model through a virtual slot.
    """
    failed_route = (failed_card.get("provider_id"), failed_card.get("model_name"))
    out = []
    seen = {failed_route}
    for card in available_cards(db):
        route = (card.get("provider_id"), card.get("model_name"))
        if route in seen:
            continue
        if card["cost_level"] != failed_card.get("cost_level"):
            continue
        seen.add(route)
        out.append(card)
    return out
