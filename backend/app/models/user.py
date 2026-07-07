import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String, default="")
    role: Mapped[str] = mapped_column(String, default="user")
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Baseline starter grant; registration overrides this from the
    # `demo_starting_credits` setting. Kept at 100 to match that default and the
    # advertised "100 credits = $1" so a bare User() is never over-granted.
    token_balance: Mapped[int] = mapped_column(Integer, default=100)
    lifetime_tokens_granted: Mapped[int] = mapped_column(Integer, default=100)
    lifetime_tokens_spent: Mapped[int] = mapped_column(Integer, default=0)
    demo_generations_remaining: Mapped[int] = mapped_column(Integer, default=1)
    # Permanent personal payment code the user sends to the payment bot; the
    # bot uses it to link this account (see telegram_id) once, then credits by id.
    pay_code: Mapped[str] = mapped_column(String(12), default="", index=True)
    # Telegram user id linked via the pay_code; the bot credits by this id.
    telegram_id: Mapped[str] = mapped_column(String(32), default="", index=True)
    signup_fingerprint: Mapped[str] = mapped_column(String, default="")
    signup_ip: Mapped[str] = mapped_column(String, default="")
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
