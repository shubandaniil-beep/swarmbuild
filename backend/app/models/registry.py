import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, Integer, Numeric, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    provider_type: Mapped[str] = mapped_column(String)  # openai|anthropic|gemini|deepseek|qwen|openrouter|custom_openai|mock
    base_url: Mapped[str] = mapped_column(String, default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    api_key_mask: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String, default="untested")  # untested|active|error
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProviderKey(Base):
    """One API key in a provider's pool. A provider (operator) can hold many
    keys — e.g. 15 Anthropic keys — that the runner rotates across to spread
    load and survive per-key rate limits."""
    __tablename__ = "provider_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(String(36), index=True)
    label: Mapped[str] = mapped_column(String, default="")
    api_key_encrypted: Mapped[str] = mapped_column(Text, default="")
    api_key_mask: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String, default="untested")  # untested|active|error
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ModelEntry(Base):
    __tablename__ = "model_registry"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String)
    provider_id: Mapped[str] = mapped_column(String(36))
    model_name: Mapped[str] = mapped_column(String)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    cost_level: Mapped[str] = mapped_column(String, default="medium")
    input_price_per_1m: Mapped[float] = mapped_column(Numeric(10, 4), default=1)
    output_price_per_1m: Mapped[float] = mapped_column(Numeric(10, 4), default=2)
    max_context_tokens: Mapped[int] = mapped_column(Integer, default=128000)
    max_output_tokens: Mapped[int] = mapped_column(Integer, default=8000)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_json: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_code: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    price_usd: Mapped[float] = mapped_column(Numeric(10, 2))
    description: Mapped[str] = mapped_column(Text, default="")
    swarm_size: Mapped[int] = mapped_column(Integer, default=4)
    max_phases: Mapped[int] = mapped_column(Integer, default=8)
    model_budget_usd: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    compute_budget_usd: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    credit_grant: Mapped[int] = mapped_column(Integer, default=0)   # credits the pack grants
    bonus_percent: Mapped[int] = mapped_column(Integer, default=0)  # bonus baked into the grant
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_project_modes: Mapped[list] = mapped_column(JSON, default=list)
    allowed_outputs: Mapped[list] = mapped_column(JSON, default=list)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProjectType(Base):
    __tablename__ = "project_types"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    key: Mapped[str] = mapped_column(String, unique=True)
    display_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_codebase: Mapped[bool] = mapped_column(Boolean, default=True)
    default_outputs: Mapped[list] = mapped_column(JSON, default=list)
    default_phases: Mapped[list] = mapped_column(JSON, default=list)
    recommended_budget_min: Mapped[float] = mapped_column(Numeric(10, 2), default=20)
    recommended_budget_max: Mapped[float] = mapped_column(Numeric(10, 2), default=200)
    template_prompt: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)  # {"v": <actual value>}
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
