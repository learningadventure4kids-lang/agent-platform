"""Agent configuration: one row per business/tenant using the platform.
The public_token is never stored in plaintext -- only its HMAC hash, so a
leaked database dump cannot be used to impersonate an agent's widget."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    public_token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    # A tenant (business) can eventually own multiple agents by sharing the
    # same tenant_id; today each agent defaults to being its own tenant
    # (tenant_id == agent_key at creation) since the platform doesn't yet
    # have a separate "organization" concept. Every knowledge-base record
    # is scoped by both tenant_id AND agent_id so that grouping agents
    # under a shared tenant later never widens knowledge access on its own.
    tenant_id: Mapped[str] = mapped_column(String(80), index=True)

    # NULL means platform/admin-owned (every agent created before the
    # self-serve builder existed, or created directly from the admin
    # dashboard) -- see app/api/builder.py, which is the only place that
    # sets this, and which also enforces that a self-serve user can only
    # ever read/modify rows where this matches their own id.
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    name: Mapped[str] = mapped_column(String(80))  # assistant's name, e.g. "Aria"
    brand_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    system_prompt: Mapped[str] = mapped_column(Text)
    welcome_message: Mapped[str] = mapped_column(Text)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)  # starter prompt chips
    lead_fields: Mapped[list] = mapped_column(JSON, default=list)  # which fields this agent collects
    theme: Mapped[dict] = mapped_column(JSON, default=dict)  # accent color etc. for the widget

    model: Mapped[str] = mapped_column(String(80), default="qwen3:8b")
    temperature: Mapped[float] = mapped_column(Float, default=0.4)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # NULL means "use the platform default provider" (see
    # app/ai/resolution.py::resolve_provider_for_agent) -- this is what
    # keeps every pre-existing agent working after this feature was added
    # without any admin action: they resolve to the seeded default Ollama
    # provider automatically. fallback_provider_id is optional and only
    # used if the primary provider fails at request time (timeout/outage/
    # rate limit -- never for invalid credentials, see resolution.py).
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("ai_providers.id"), nullable=True)
    fallback_provider_id: Mapped[int | None] = mapped_column(ForeignKey("ai_providers.id"), nullable=True)

    allowed_domains: Mapped[list] = mapped_column(JSON, default=list)  # [] == no restriction

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
