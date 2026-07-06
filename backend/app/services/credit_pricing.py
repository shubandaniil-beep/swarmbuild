"""Credit pricing: the user-facing currency layer.

Users see clean, predictable **credits** (1 credit = $0.01 by default). Each
phase burns a fixed, round number of credits regardless of how many times an
agent internally retried — so a stubborn agent eats internal USD margin, never
the user's balance. The founder sees real USD cost + margin underneath.
"""
from sqlalchemy.orm import Session

from .settings_service import get_setting

# Relative phase weights. The final user-facing estimate is scaled to the
# selected tariff/budget, so Heavy Build is materially larger than Trial.
PHASE_WEIGHTS: dict[str, int] = {
    "intake": 150,
    "swarm_understanding": 180,   # idea analysis
    "spec_war": 320,              # spec / ТЗ
    "architecture_battle": 450,   # architecture
    "build_sprint": 1400,         # build / generation
    "review_stop": 600,           # review
    "repair_sprint": 800,         # repair
    "final_audit": 400,           # final audit
    "packaging": 250,             # packaging + export
}

# Human labels for the itemized breakdown shown before/after a run.
PHASE_LABELS: dict[str, str] = {
    "intake": "Приём и оценка",
    "swarm_understanding": "Анализ идеи",
    "spec_war": "Техническое задание",
    "architecture_battle": "Архитектура",
    "build_sprint": "Сборка",
    "review_stop": "Ревью",
    "repair_sprint": "Доработка",
    "final_audit": "Финальный аудит",
    "packaging": "Упаковка и экспорт",
}

_DEFAULT_TOKENS_PER_USD = 100
_ESTIMATE_SPREAD = 0.15  # ±15% band shown as the estimate range


def tokens_per_usd(db: Session) -> int:
    return int(get_setting(db, "tokens_per_usd") or _DEFAULT_TOKENS_PER_USD)


def credits_to_usd(db: Session, credits: float) -> float:
    return round(credits / max(tokens_per_usd(db), 1), 6)


def usd_to_credits(db: Session, usd: float) -> int:
    return max(0, round(usd * tokens_per_usd(db)))


def quote_credits_for_budget(db: Session | None, budget_usd: float) -> int:
    """Public quote for a selected package. Prefer admin-managed tariffs; fall
    back to the 100 credits = $1 base rate for custom/simple installs."""
    if db is not None:
        from ..models import Tariff
        tariffs = (db.query(Tariff).filter(Tariff.enabled.is_(True))
                   .order_by(Tariff.price_usd.asc()).all())
        chosen = None
        for tariff in tariffs:
            if float(tariff.price_usd) <= budget_usd:
                chosen = tariff
        if chosen is None and tariffs:
            chosen = tariffs[0]
        if chosen is not None and chosen.credit_grant:
            return int(chosen.credit_grant)
    per_usd = tokens_per_usd(db) if db is not None else _DEFAULT_TOKENS_PER_USD
    return max(100, round(budget_usd * per_usd))


def phase_weight(phase_key: str) -> int:
    return PHASE_WEIGHTS.get(phase_key, 200)


def phase_credits(phase_key: str, phase_keys: list[str] | None = None,
                  project_total: int | None = None) -> int:
    if not phase_keys or not project_total:
        return phase_weight(phase_key)
    total_weight = sum(phase_weight(p) for p in phase_keys) or 1
    return max(1, round(project_total * phase_weight(phase_key) / total_weight))


def breakdown(phase_keys: list[str], total_credits: int | None = None) -> list[dict]:
    """Itemized per-phase credit cost for the given pipeline."""
    if total_credits is None:
        total_credits = sum(phase_weight(p) for p in phase_keys)
    items = []
    allocated = 0
    for idx, phase in enumerate(phase_keys):
        if idx == len(phase_keys) - 1:
            credits = max(1, total_credits - allocated)
        else:
            credits = phase_credits(phase, phase_keys, total_credits)
            allocated += credits
        items.append({"phase_key": phase, "label": PHASE_LABELS.get(phase, phase),
                      "credits": credits})
    return items


def estimate(phase_keys: list[str], budget_usd: float | None = None,
             db: Session | None = None) -> dict:
    """Total credit estimate for a pipeline, with a ±band range."""
    total = (quote_credits_for_budget(db, budget_usd)
             if budget_usd is not None else sum(phase_weight(p) for p in phase_keys))
    items = breakdown(phase_keys, total)
    return {
        "phases": items,
        "credits_estimate": total,
        "credits_min": int(round(total * (1 - _ESTIMATE_SPREAD))),
        "credits_max": int(round(total * (1 + _ESTIMATE_SPREAD))),
        "credits_per_usd": tokens_per_usd(db) if db is not None else _DEFAULT_TOKENS_PER_USD,
        "usd_equivalent": credits_to_usd(db, total) if db is not None else round(total / _DEFAULT_TOKENS_PER_USD, 2),
    }


def surcharge_risk(credits_estimate_max: int, balance: int) -> str:
    """How likely the user is to need a top-up mid-project."""
    if balance >= credits_estimate_max:
        return "low"
    if balance >= credits_estimate_max * 0.7:
        return "medium"
    return "high"
