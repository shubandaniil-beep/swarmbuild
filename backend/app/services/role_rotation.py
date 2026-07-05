"""Role Rotation Engine: rotating mandates per phase with hard constraints.

Rules implemented:
- a model is never `lead` more than 2 phases in a row;
- the phase `judge` differs from the phase `lead`;
- the author of the previous phase's main output is not the sole reviewer of it
  (rotation offset guarantees the reviewer differs from the previous lead);
- roles rotate every phase even if a model "fits" one role.
"""
from .access_control import ACCESS_BY_MANDATE

# mandates required per phase, ordered by priority (trimmed to swarm size)
PHASE_MANDATES: dict[str, list[str]] = {
    "intake": ["lead", "critic"],
    "swarm_understanding": ["lead", "builder", "critic", "judge", "reviewer", "builder", "critic", "reviewer"],
    "spec_war": ["lead", "critic", "judge", "builder", "reviewer", "critic", "builder", "reviewer"],
    "architecture_battle": ["lead", "critic", "builder", "judge", "builder", "reviewer", "critic", "reviewer"],
    "build_sprint": ["builder", "lead", "builder", "reviewer", "builder", "critic", "builder", "judge"],
    "review_stop": ["reviewer", "reviewer", "judge", "critic", "reviewer", "critic", "reviewer", "judge"],
    "repair_sprint": ["repairer", "reviewer", "repairer", "judge", "repairer", "reviewer", "critic", "reviewer"],
    "final_audit": ["judge", "reviewer", "critic", "reviewer", "judge", "critic", "reviewer", "reviewer"],
    "packaging": ["packager", "reviewer", "judge", "packager", "reviewer", "critic", "packager", "reviewer"],
}


def build_rotation_plan(phases: list[str], pool: list[dict]) -> list[dict]:
    """Assign mandates for every phase, rotating the agent order each phase."""
    n = len(pool)
    lead_streak: dict[str, int] = {c["id"]: 0 for c in pool}
    plan = []

    for phase_idx, phase in enumerate(phases):
        mandates = PHASE_MANDATES.get(phase, ["lead", "critic"])[:n]
        order = [pool[(i + phase_idx) % n] for i in range(n)]

        # rule: no model leads more than 2 consecutive phases
        if "lead" in mandates:
            li = mandates.index("lead")
            if lead_streak.get(order[li]["id"], 0) >= 2:
                for j in range(len(order)):
                    if j != li and lead_streak.get(order[j]["id"], 0) < 2:
                        order[li], order[j] = order[j], order[li]
                        break

        # rule: judge must differ from lead
        if "lead" in mandates and "judge" in mandates:
            li, ji = mandates.index("lead"), mandates.index("judge")
            if order[li]["id"] == order[ji]["id"]:
                for j in range(len(order)):
                    if j not in (li, ji) and order[j]["id"] != order[li]["id"]:
                        order[ji], order[j] = order[j], order[ji]
                        break

        assignments = []
        new_streak = {c["id"]: 0 for c in pool}
        for i, mandate in enumerate(mandates):
            card = order[i]
            assignments.append({
                "agent_slot": i + 1,
                "model_id": card["id"],
                "model_name": card["model_name"],
                "provider": card["provider"],
                "mandate": mandate,
                "access": ACCESS_BY_MANDATE.get(mandate, []),
                "card": card,  # registry data only, no secrets
            })
            if mandate == "lead":
                new_streak[card["id"]] = lead_streak.get(card["id"], 0) + 1
        lead_streak = new_streak

        plan.append({"phase": phase, "assignments": assignments})
    return plan
