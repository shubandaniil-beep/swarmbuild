import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def now() -> datetime:
    return datetime.now(UTC)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    artifact_type: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    display_name: Mapped[str] = mapped_column(String)
    # quarantine | safe_to_download | blocked
    safety_status: Mapped[str] = mapped_column(String, default="safe_to_download")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
