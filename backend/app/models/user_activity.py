import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class UserActivity(Base):
    __tablename__ = "user_activity"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    email: Mapped[str] = mapped_column(String, default="")
    action: Mapped[str] = mapped_column(String, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
