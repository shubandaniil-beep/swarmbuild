"""Per-user payment codes, Telegram linking, and bot-driven crediting.

Every account owns one permanent 6-digit `pay_code`, generated at registration.
The user sends this code to the payment bot once; the bot links their
`telegram_id` to the account via that code. After each Stars payment the bot
credits by `telegram_id`. Crediting is idempotent per `external_id` so bot
retries never double-credit.
"""

import secrets
from datetime import UTC, datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from ..models import CreditTopup, User

CODE_LENGTH = 6
_MAX_ATTEMPTS = 30


class PayCodeError(Exception):
    """Raised when a pay-code operation cannot complete."""


class InvalidLinkCode(PayCodeError):
    """The link code is unknown, or the telegram id is already taken."""


class AccountNotLinked(PayCodeError):
    """No account is linked to the given telegram id."""


def normalize(raw: str) -> str:
    """Keep digits only, so '12 34-56' and '123456' resolve to one code."""
    return "".join(ch for ch in (raw or "") if ch.isdigit())


def _random_code() -> str:
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


def generate_unique_code(db: Session) -> str:
    """A 6-digit code not currently assigned to any user."""
    for _ in range(_MAX_ATTEMPTS):
        code = _random_code()
        if not db.query(User.id).filter(User.pay_code == code).first():
            return code
    raise PayCodeError("could not allocate a unique pay code")


def ensure_pay_code(db: Session, user: User) -> str:
    """Return the user's pay code, generating and persisting one if missing."""
    if user.pay_code:
        return user.pay_code
    code = generate_unique_code(db)
    user.pay_code = code
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.pay_code


def backfill_pay_codes(db: Session) -> int:
    """Assign codes to any pre-existing users that lack one. Returns count."""
    missing = db.query(User).filter((User.pay_code == "") | (User.pay_code.is_(None))).all()
    for user in missing:
        user.pay_code = generate_unique_code(db)
        db.add(user)
        db.flush()
    if missing:
        db.commit()
    return len(missing)


def link_telegram(db: Session, *, code: str, telegram_id: str) -> User:
    """Bind `telegram_id` to the account owning `code`. Returns the user.

    Idempotent: re-linking the same telegram id to the same account is fine.
    Raises InvalidLinkCode if the code is unknown or the telegram id already
    belongs to a different account.
    """
    normalized = normalize(code)
    tg = str(telegram_id or "").strip()
    if len(normalized) != CODE_LENGTH:
        raise InvalidLinkCode("код должен состоять из 6 цифр")
    if not tg:
        raise InvalidLinkCode("не передан telegram_id")

    user = db.query(User).filter(User.pay_code == normalized).one_or_none()
    if user is None:
        raise InvalidLinkCode("код не найден")

    other = (db.query(User)
             .filter(User.telegram_id == tg, User.id != user.id)
             .first())
    if other is not None:
        raise InvalidLinkCode("этот Telegram уже привязан к другому аккаунту")

    if user.telegram_id != tg:
        user.telegram_id = tg
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def credit_by_telegram_id(db: Session, *, telegram_id: str, credits: int,
                          amount_usd: float, external_id: str) -> dict:
    """Credit the account linked to `telegram_id`. Idempotent on `external_id`.

    Returns {"status": "credited"|"duplicate", "user_id", "credits", "balance"}.
    Raises AccountNotLinked if no account is linked to this telegram id.
    """
    tg = str(telegram_id or "").strip()
    if credits <= 0:
        raise PayCodeError("credits must be positive")

    user = db.query(User).filter(User.telegram_id == tg).one_or_none()
    if user is None:
        raise AccountNotLinked(f"telegram_id {tg} не привязан")

    ref = (external_id or "").strip()
    if ref:
        existing = (db.query(CreditTopup)
                    .filter(CreditTopup.provider == "telegram_stars",
                            CreditTopup.provider_ref == ref,
                            CreditTopup.status == "paid")
                    .first())
        if existing is not None:
            # Bot retried an already-processed payment — do not credit twice.
            return {"status": "duplicate", "user_id": user.id,
                    "credits": existing.credits, "balance": user.token_balance}

    now = datetime.now(UTC)
    db.execute(
        update(User)
        .where(User.id == user.id)
        .values(
            token_balance=User.token_balance + credits,
            lifetime_tokens_granted=User.lifetime_tokens_granted + credits,
        )
        .execution_options(synchronize_session=False)
    )
    db.add(CreditTopup(
        user_id=user.id, email=user.email, credits=credits, amount_usd=amount_usd,
        provider="telegram_stars", provider_ref=ref, status="paid", paid_at=now,
    ))
    db.commit()
    db.refresh(user)

    return {"status": "credited", "user_id": user.id, "credits": credits,
            "balance": user.token_balance}


def balance_for_telegram(db: Session, *, telegram_id: str) -> int:
    """Current credit balance for the account linked to `telegram_id`."""
    tg = str(telegram_id or "").strip()
    user = db.query(User).filter(User.telegram_id == tg).one_or_none()
    if user is None:
        raise AccountNotLinked(f"telegram_id {tg} не привязан")
    return user.token_balance or 0
