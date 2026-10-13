"""A session is scoped to exactly one agent -- the same visitor talking to
two different agents (e.g. Kaur Jewellery and Astrology widgets on
different sites) gets two separate sessions, never a shared one, so
conversation context and collected fields never leak between tenants."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=_uuid)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)

    # Free-form structured bag: collected_fields, pending_lead flag, etc.
    # (see app/agents/state.py). Never stores chain-of-thought.
    session_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    conversation_status: Mapped[str] = mapped_column(String(40), default="new")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
