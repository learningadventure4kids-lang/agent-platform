"""A knowledge base groups the documents an agent can draw on when
answering business-specific questions. Today the platform auto-creates
exactly one knowledge base per agent (see
app/rag/knowledge_base_service.py::get_or_create_default), but the schema
allows more than one per agent later (e.g. separate "public FAQ" vs.
"internal policy" bases) without a migration."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)

    name: Mapped[str] = mapped_column(String(120), default="Default knowledge base")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
