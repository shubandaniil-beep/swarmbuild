import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class ProjectPhase(Base):
    __tablename__ = "project_phases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    phase_key: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    budget_limit_usd: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    spent_estimated_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)
    # Honest progress accounting (spec §7.7): an LLM call is not progress. A phase
    # only "made progress" when it produced parsed files / substantive artifacts /
    # passed checks / closed open tasks. Credits are charged only when it did.
    made_progress: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_proof: Mapped[dict] = mapped_column(JSON, default=dict)
    gate_results: Mapped[dict] = mapped_column(JSON, default=dict)
    credits_charged: Mapped[int] = mapped_column(Integer, default=0)
