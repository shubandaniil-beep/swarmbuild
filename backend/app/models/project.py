import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Numeric, Integer, DateTime, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column


from ..database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    title: Mapped[str] = mapped_column(String)
    brief: Mapped[str] = mapped_column(Text)
    budget_usd: Mapped[float] = mapped_column(Numeric(10, 2))
    requested_outputs: Mapped[list] = mapped_column(JSON, default=list)
    project_type: Mapped[str] = mapped_column(String, default="auto")
    project_mode: Mapped[str] = mapped_column(String, default="auto")  # code|document|business|mixed|auto
    requires_codebase: Mapped[bool] = mapped_column(Boolean, default=True)
    technical_level: Mapped[str] = mapped_column(String, default="non_technical")
    personality_mode: Mapped[str] = mapped_column(String, default="balanced")  # swarm build-style
    user_goal: Mapped[str] = mapped_column(Text, default="")
    parent_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="draft")
    complexity: Mapped[str] = mapped_column(String, default="medium")
    swarm_size: Mapped[int] = mapped_column(Integer, default=4)
    current_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    # credit accounting: user sees credits, founder sees usd + margin
    credits_estimate: Mapped[int] = mapped_column(Integer, default=0)
    credits_spent: Mapped[int] = mapped_column(Integer, default=0)
    estimated_usd_cost: Mapped[float] = mapped_column(Numeric(10, 6), default=0)
    demo_run: Mapped[bool] = mapped_column(Boolean, default=False)  # one-time trial slot; still burns credits
    risk_level: Mapped[str] = mapped_column(String, default="low")  # prompt-injection risk: low|medium|high
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
