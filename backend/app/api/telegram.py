"""Payment-bot integration endpoints.

Matches the contract the Telegram Stars bot expects (see the bot's site_api.py):
  POST /api/telegram/link    {code, telegram_id}           -> {success, username}
  POST /api/telegram/credit  {telegram_id, amount, external_id} -> {success, balance}
  GET  /api/telegram/balance?telegram_id=...               -> {balance}

All three are authenticated with `Authorization: Bearer <PAYMENT_BOT_SECRET>`
(the bot's SITE_API_KEY must equal this value). Empty secret ⇒ disabled.
"""
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import User
from ..services import credit_pricing, pay_codes
from ..services.user_activity import log_user_activity

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


def require_bot_secret(authorization: str = Header(default="")) -> None:
    secret = settings.PAYMENT_BOT_SECRET
    if not secret:
        raise HTTPException(503, "telegram bot integration is not configured")
    prefix = "Bearer "
    token = authorization[len(prefix):] if authorization.startswith(prefix) else ""
    if not token or not secrets.compare_digest(token, secret):
        raise HTTPException(401, "bad bot secret")


class LinkBody(BaseModel):
    code: str = Field(min_length=4, max_length=20)
    telegram_id: int | str


class CreditBody(BaseModel):
    telegram_id: int | str
    amount: float = Field(gt=0, le=10_000_000)
    external_id: str = Field(default="", max_length=200)


def _display_name(user: User) -> str:
    return (user.email or "").split("@")[0] or "user"


@router.post("/link")
def link(body: LinkBody, _: None = Depends(require_bot_secret),
         db: Session = Depends(get_db)):
    try:
        user = pay_codes.link_telegram(db, code=body.code,
                                       telegram_id=str(body.telegram_id))
    except pay_codes.InvalidLinkCode as exc:
        # 400 with {"error": ...} — the bot surfaces this text to the user.
        raise HTTPException(400, detail={"error": str(exc)}) from exc
    log_user_activity(db, user, "telegram_linked",
                      meta={"telegram_id": str(body.telegram_id)})
    return {"success": True, "username": _display_name(user)}


@router.post("/credit")
def credit(body: CreditBody, _: None = Depends(require_bot_secret),
           db: Session = Depends(get_db)):
    credits = int(round(body.amount))
    if credits <= 0:
        raise HTTPException(400, "amount too small")
    amount_usd = credit_pricing.credits_to_usd(db, credits)
    try:
        result = pay_codes.credit_by_telegram_id(
            db, telegram_id=str(body.telegram_id), credits=credits,
            amount_usd=amount_usd, external_id=body.external_id)
    except pay_codes.AccountNotLinked as exc:
        # 404 tells the bot to ask the user to link their Telegram first.
        raise HTTPException(404, str(exc)) from exc
    except pay_codes.PayCodeError as exc:
        raise HTTPException(400, str(exc)) from exc

    if result["status"] == "credited":
        user = db.get(User, result["user_id"])
        log_user_activity(db, user, "topup_credited",
                          meta={"credits": result["credits"], "amount_usd": amount_usd,
                                "provider": "telegram_stars",
                                "external_id": body.external_id})
    return {"success": True, "balance": result["balance"]}


@router.get("/balance")
def balance(telegram_id: int | str, _: None = Depends(require_bot_secret),
            db: Session = Depends(get_db)):
    try:
        bal = pay_codes.balance_for_telegram(db, telegram_id=str(telegram_id))
    except pay_codes.AccountNotLinked as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"balance": bal}
