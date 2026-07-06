"""Unit tests for the swarm core: budget rules and role-rotation constraints."""
from app.services.budget_engine import build_budget_state, estimate_complexity, plan_swarm
from app.services.role_rotation import build_rotation_plan


def _pool(n: int) -> list[dict]:
    return [{"id": f"m{i}", "model_name": f"model-{i}", "provider": "mock"} for i in range(n)]


def test_swarm_size_scales_with_budget():
    # No DB: exercises the spec fallback rules (<25 → 3, <60 → 4, <150 → 6, else 8).
    assert plan_swarm(10)[0] == 3
    assert plan_swarm(40)[0] == 4
    assert plan_swarm(100)[0] == 6
    assert plan_swarm(300)[0] == 8


def test_budget_split_adds_up():
    state = build_budget_state("p1", 100)
    parts = (state["platform_fee_usd"] + state["model_budget_usd"]
             + state["compute_budget_usd"] + state["reserve_budget_usd"])
    assert round(parts, 2) == 100
    assert state["remaining_usd"] > 0
    assert state["status"] == "active"


def test_complexity_estimate_bounds():
    assert estimate_complexity("сайт", 10) in ("low", "medium", "high")
    long_brief = "CRM бот сайт калькулятор план презентация api " * 30
    assert estimate_complexity(long_brief, 200) == "high"


def test_rotation_lead_streak_capped():
    _, phases = plan_swarm(100)
    plan = build_rotation_plan(phases, _pool(4))
    streaks: dict[str, int] = {}
    for phase in plan:
        leads = [a["model_id"] for a in phase["assignments"] if a["mandate"] == "lead"]
        for model in {a["model_id"] for a in phase["assignments"]}:
            if model in leads:
                streaks[model] = streaks.get(model, 0) + 1
                assert streaks[model] <= 2, f"{model} led more than 2 phases in a row"
            else:
                streaks[model] = 0


def test_rotation_judge_differs_from_lead():
    _, phases = plan_swarm(100)
    plan = build_rotation_plan(phases, _pool(4))
    for phase in plan:
        by_mandate: dict[str, list[str]] = {}
        for a in phase["assignments"]:
            by_mandate.setdefault(a["mandate"], []).append(a["model_id"])
        if "lead" in by_mandate and "judge" in by_mandate:
            assert set(by_mandate["lead"]).isdisjoint(by_mandate["judge"]), phase["phase"]


def test_rotation_roles_change_between_phases():
    _, phases = plan_swarm(100)
    plan = build_rotation_plan(phases, _pool(4))
    mandate_history: dict[str, set[str]] = {}
    for phase in plan:
        for a in phase["assignments"]:
            mandate_history.setdefault(a["model_id"], set()).add(a["mandate"])
    # every agent should have worked in more than one role across the pipeline
    for model, mandates in mandate_history.items():
        assert len(mandates) > 1, f"{model} was stuck in a single role: {mandates}"
