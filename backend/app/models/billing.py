import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class CreditTopup(Base):
    __tablename__ = "credit_topups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    email: Mapped[str] = mapped_column(String, default="")
    credits: Mapped[int] = mapped_column(Integer, default=0)
    amount_usd: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    provider: Mapped[str] = mapped_column(String, default="telegram_stars")
    provider_ref: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|paid|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
