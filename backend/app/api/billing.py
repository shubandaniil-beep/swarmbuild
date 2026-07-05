from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CreditTopup, User
from ..services import credit_pricing
from ..services.settings_service import get_setting
from ..services.user_activity import log_user_activity
from .deps import get_current_user

router = APIRouter(prefix="/api/billing", tags=["billing"])


TOPUP_PACKS = [
    {"id": "starter", "credits": 1000, "label": "Starter", "best_for": "первые доработки"},
    {"id": "builder", "credits": 5000, "label": "Builder", "best_for": "несколько небольших задач"},
    {"id": "standard", "credits": 12000, "label": "Standard", "best_for": "полный MVP-пакет"},
    {"id": "heavy", "credits": 26000, "label": "Heavy", "best_for": "тяжёлая сборка"},
]


class TopupBody(BaseModel):
    credits: int = Field(gt=0, le=1_000_000)
    provider: str = Field(default="telegram_stars", max_length=40)


def _payment_url(db: Session, topup_id: str) -> str:
    base = str(get_setting(db, "telegram_payment_bot_url") or "").strip()
    if not base:
        return ""
    separator = "&start=" if "?" in base else "?start="
    return f"{base}{separator}topup_{topup_id}"


def _pack_out(db: Session, pack: dict) -> dict:
    credits = int(pack["credits"])
    amount = credit_pricing.credits_to_usd(db, credits)
    return {**pack, "amount_usd": amount,
            "display": f"{credits:,}".replace(",", " ") + f" credits = ${amount:g}"}


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    credits_per_usd = credit_pricing.tokens_per_usd(db)
    return {
        "token_balance": user.token_balance or 0,
        "demo_generations_remaining": user.demo_generations_remaining or 0,
        "credits_per_usd": credits_per_usd,
        "credit_value_usd": round(1 / max(credits_per_usd, 1), 4),
        "currency": get_setting(db, "default_currency") or "USD",
        "packs": [_pack_out(db, p) for p in TOPUP_PACKS],
        "payment_provider": "telegram_stars",
        "payment_status": "manual_pending",
        "payment_note": "Telegram Stars подключается через бота; сейчас создаётся заявка на пополнение.",
    }


@router.get("/topups")
def my_topups(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(CreditTopup).filter(CreditTopup.user_id == user.id)
            .order_by(CreditTopup.created_at.desc()).limit(50).all())
    return [_topup_out(db, row) for row in rows]


@router.post("/topups")
def create_topup(body: TopupBody, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    allowed = {p["credits"] for p in TOPUP_PACKS}
    if body.credits not in allowed:
        raise HTTPException(400, "unsupported top-up pack")
    row = CreditTopup(
        user_id=user.id,
        email=user.email,
        credits=body.credits,
        amount_usd=credit_pricing.credits_to_usd(db, body.credits),
        provider=body.provider,
        status="pending",
    )
    db.add(row)
    db.commit()
    log_user_activity(db, user, "topup_requested",
                      meta={"topup_id": row.id, "credits": row.credits,
                            "amount_usd": float(row.amount_usd),
                            "provider": row.provider})
    return _topup_out(db, row)


def _topup_out(db: Session, row: CreditTopup) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "credits": row.credits,
        "amount_usd": float(row.amount_usd),
        "provider": row.provider,
        "provider_ref": row.provider_ref,
        "status": row.status,
        "payment_url": _payment_url(db, row.id) if row.status == "pending" else "",
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "paid_at": row.paid_at.isoformat() if row.paid_at else None,
    }
