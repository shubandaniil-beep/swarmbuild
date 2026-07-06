from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..models import AgentCall, Project, User
from . import credit_pricing
from .settings_service import get_setting
from .user_activity import log_user_activity

DEMO_PROJECT_BUDGET_USD = 5


def tokens_for_budget(db: Session, budget_usd: float) -> int:
    tokens_per_usd = int(get_setting(db, "tokens_per_usd") or 100)
    return max(1, int(round(budget_usd * tokens_per_usd)))


def ensure_credit_columns(user: User, demo_credits: int = 100) -> None:
    if user.token_balance is None:
        user.token_balance = demo_credits
    if user.lifetime_tokens_granted is None:
        user.lifetime_tokens_granted = demo_credits
    if user.lifetime_tokens_spent is None:
        user.lifetime_tokens_spent = 0
    if user.demo_generations_remaining is None:
        user.demo_generations_remaining = 1


def debit_project_tokens(db: Session, user: User, budget_usd: float,
                         project_title: str) -> dict:
    demo_credits = int(get_setting(db, "demo_starting_credits") or 100)
    ensure_credit_columns(user, demo_credits)
    if user.role == "admin":
        return {"tokens_required": 0, "token_balance": user.token_balance,
                "demo_used": False, "admin_bypass": True}

    tokens = tokens_for_budget(db, budget_usd)
    demo_used = False
    if budget_usd <= DEMO_PROJECT_BUDGET_USD and user.demo_generations_remaining > 0:
        demo_used = True
        user.demo_generations_remaining -= 1

    if user.token_balance < tokens:
        raise HTTPException(
            402,
            {
                "message": "not enough SwarmBuild credits",
                "tokens_required": tokens,
                "token_balance": user.token_balance,
            },
        )

    user.token_balance -= tokens
    user.lifetime_tokens_spent += tokens
    db.commit()
    log_user_activity(db, user, "tokens_debited", meta={
        "project_title": project_title,
        "budget_usd": budget_usd,
        "tokens": tokens,
        "demo_used": demo_used,
        "remaining": user.token_balance,
    })
    return {"tokens_required": tokens, "token_balance": user.token_balance,
            "demo_used": demo_used, "admin_bypass": False}


def authorize_project_credits(db: Session, user: User, phase_keys: list[str],
                              budget_usd: float, project_title: str) -> dict:
    """Pre-run check for the metered model: no upfront debit — credits are burned
    per phase as work completes. Verifies the user can start, and consumes the
    one-time trial slot for tiny projects. The trial still spends starter credits
    as phases complete; it is not a second free balance."""
    demo_credits = int(get_setting(db, "demo_starting_credits") or 100)
    ensure_credit_columns(user, demo_credits)
    est = credit_pricing.estimate(phase_keys, budget_usd=budget_usd, db=db)

    if user.role == "admin":
        return {"demo_run": False, "admin_bypass": True, **est,
                "token_balance": user.token_balance,
                "surcharge_risk": "low"}

    # Trial run for tiny projects while a demo generation remains. It spends the
    # starter balance per phase, so the user sees honest credit accounting.
    if budget_usd <= DEMO_PROJECT_BUDGET_USD and user.demo_generations_remaining > 0:
        if user.token_balance < est["credits_estimate"]:
            raise HTTPException(402, {
                "message": "not enough SwarmBuild credits for the trial project",
                "credits_required": est["credits_estimate"],
                "credits_estimate": est["credits_estimate"],
                "token_balance": user.token_balance,
            })
        user.demo_generations_remaining -= 1
        db.commit()
        log_user_activity(db, user, "trial_run_started",
                          meta={"project_title": project_title, **est})
        return {"demo_run": True, "admin_bypass": False, **est,
                "token_balance": user.token_balance, "surcharge_risk": "low"}

    if user.token_balance < est["credits_min"]:
        raise HTTPException(402, {
            "message": "not enough SwarmBuild credits to start this project",
            "credits_required": est["credits_min"],
            "credits_estimate": est["credits_estimate"],
            "token_balance": user.token_balance,
        })

    return {"demo_run": False, "admin_bypass": False, **est,
            "token_balance": user.token_balance,
            "surcharge_risk": credit_pricing.surcharge_risk(est["credits_max"], user.token_balance)}


def charge_phase_credits(db: Session, project: Project, phase_key: str) -> dict:
    """Burn a fixed number of credits for a completed phase and refresh the
    project's internal USD cost. Fixed per-phase pricing means a stubborn agent
    that retries a lot eats internal margin, never the user's balance. Returns
    {"stopped": True} when a non-demo user can no longer afford the next phase."""
    from ..models import ProjectPhase
    phase_keys = [p.phase_key for p in
                  db.query(ProjectPhase).filter(ProjectPhase.project_id == project.id).all()]
    credits = credit_pricing.phase_credits(
        phase_key, phase_keys, project.credits_estimate or None)
    calls = db.query(AgentCall).filter(AgentCall.project_id == project.id).all()
    project.estimated_usd_cost = round(sum(float(c.cost_estimated_usd) for c in calls), 6)

    user = db.get(User, project.user_id) if project.user_id else None
    if user is None or user.role == "admin":
        db.commit()
        return {"stopped": False, "charged": 0, "demo": bool(project.demo_run),
                "credits_spent": project.credits_spent}

    if user.token_balance < credits:
        db.commit()
        return {"stopped": True, "charged": 0, "shortfall": credits - user.token_balance,
                "credits_spent": project.credits_spent, "token_balance": user.token_balance}

    user.token_balance -= credits
    user.lifetime_tokens_spent += credits
    project.credits_spent += credits
    db.commit()
    return {"stopped": False, "charged": credits, "demo": False,
            "credits_spent": project.credits_spent, "token_balance": user.token_balance}
