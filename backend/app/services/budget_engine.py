"""Budget Engine: splits the user budget, sizes the swarm, tracks spend."""
import json
from pathlib import Path

from ..config import settings

SHORT_PHASES = ["intake", "spec_war", "build_sprint", "review_stop", "packaging"]
BASIC_PHASES = ["intake", "swarm_understanding", "spec_war", "architecture_battle",
                "build_sprint", "review_stop", "final_audit", "packaging"]
FULL_PHASES = ["intake", "swarm_understanding", "spec_war", "architecture_battle",
               "build_sprint", "review_stop", "repair_sprint", "final_audit", "packaging"]


def _phases_for(max_phases: int) -> list[str]:
    if max_phases >= 9:
        return FULL_PHASES
    if max_phases >= 8:
        return BASIC_PHASES
    return SHORT_PHASES


def plan_swarm(budget_usd: float, db=None) -> tuple[int, list[str]]:
    """Pick swarm size + phases from the tariff registry; fall back to the
    hardcoded spec rules when no tariffs exist."""
    if db is not None:
        from ..models import Tariff
        tariffs = (db.query(Tariff).filter(Tariff.enabled.is_(True))
                   .order_by(Tariff.price_usd.asc()).all())
        chosen = None
        for t in tariffs:
            if float(t.price_usd) <= budget_usd:
                chosen = t
        if chosen is None and tariffs:
            chosen = tariffs[0]
        if chosen is not None:
            return chosen.swarm_size, _phases_for(chosen.max_phases)

    if budget_usd < 25:
        return 3, SHORT_PHASES
    if budget_usd < 60:
        return 4, BASIC_PHASES
    if budget_usd < 150:
        return 6, FULL_PHASES
    return 8, FULL_PHASES


def build_budget_state(project_id: str, budget_usd: float) -> dict:
    fee = round(budget_usd * settings.PLATFORM_FEE_PERCENT / 100, 2)
    model = round(budget_usd * 0.50, 2)
    compute = round(budget_usd * 0.10, 2)
    reserve = round(budget_usd - fee - model - compute, 2)
    return {
        "project_id": project_id,
        "user_budget_usd": budget_usd,
        "platform_fee_usd": fee,
        "model_budget_usd": model,
        "compute_budget_usd": compute,
        "reserve_budget_usd": reserve,
        "spent_usd": 0.0,
        "remaining_usd": round(model + compute + reserve, 2),
        "saving_mode": False,
        "status": "active",
    }


def load_budget_state(workspace: Path) -> dict:
    return json.loads((workspace / "budget_state.json").read_text())


def save_budget_state(workspace: Path, state: dict) -> None:
    (workspace / "budget_state.json").write_text(json.dumps(state, indent=2, ensure_ascii=False))


def record_spend(workspace: Path, amount_usd: float) -> dict:
    """Add spend, flip saving mode at 85% of model budget, exhaust at 100%."""
    state = load_budget_state(workspace)
    state["spent_usd"] = round(state["spent_usd"] + amount_usd, 6)
    state["remaining_usd"] = round(
        state["model_budget_usd"] + state["compute_budget_usd"] + state["reserve_budget_usd"]
        - state["spent_usd"], 6)
    model_budget = state["model_budget_usd"] or 1
    if state["spent_usd"] >= model_budget:
        state["status"] = "exhausted"
    elif state["spent_usd"] >= 0.85 * model_budget:
        state["saving_mode"] = True
    save_budget_state(workspace, state)
    return state


def estimate_complexity(brief: str, budget_usd: float) -> str:
    words = len(brief.split())
    wanted = sum(k in brief.lower() for k in
                 ("crm", "бот", "bot", "сайт", "site", "калькулятор", "calculator",
                  "план", "plan", "презентац", "pitch", "api"))
    score = (words // 40) + wanted + (1 if budget_usd >= 100 else 0)
    if score <= 2:
        return "low"
    if score <= 5:
        return "medium"
    return "high"
