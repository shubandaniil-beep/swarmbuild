import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def now() -> datetime:
    return datetime.now(UTC)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    model_id: Mapped[str] = mapped_column(String)
    agent_name: Mapped[str] = mapped_column(String)
    current_mandate: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AgentCall(Base):
    __tablename__ = "agent_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    phase_key: Mapped[str] = mapped_column(String)
    agent_id: Mapped[str] = mapped_column(String(36))
    model_id: Mapped[str] = mapped_column(String)
    mandate: Mapped[str] = mapped_column(String)
    prompt_path: Mapped[str | None] = mapped_column(String, nullable=True)
    output_path: Mapped[str | None] = mapped_column(String, nullable=True)
    input_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens_estimated: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimated_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    status: Mapped[str] = mapped_column(String, default="success")
    provider_id: Mapped[str] = mapped_column(String, default="")
    provider_type: Mapped[str] = mapped_column(String, default="")
    provider_model_name: Mapped[str] = mapped_column(String, default="")
    provider_key_id: Mapped[str] = mapped_column(String, default="")
    provider_key_mask: Mapped[str] = mapped_column(String, default="")
    error_message: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
