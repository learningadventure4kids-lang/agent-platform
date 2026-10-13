"""Optional, agent-specific structured record (e.g. an astrology
consultation request). Not every agent uses this -- jewellery and real
estate agents in the sample set only ever create Leads."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Consultation(Base):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)

    type: Mapped[str] = mapped_column(String(60))  # e.g. "astrology"
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="new")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
