"""Audit trail for every tool call the LangGraph orchestration layer makes
(or refuses to make). One row per attempted call, written by
app/services/tool_audit_service.py from inside the graph's `execute_tool`
node -- regardless of outcome, so "the LLM said it called a tool but
nothing happened" and "a confirmation-required tool was correctly denied"
are both visible here, not just in the text logs.

Arguments and results are sanitized before being written (sensitive keys
redacted to a boolean presence flag, everything truncated) -- this table
is safe to show in the admin dashboard and is never a place secrets or
full PII end up."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base

STATUS_SUCCESS = "success"
STATUS_DENIED = "denied"
STATUS_ERROR = "error"
STATUS_TIMEOUT = "timeout"


class ToolExecutionLog(Base):
    __tablename__ = "tool_execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    tool_name: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    error_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    sanitized_arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    sanitized_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
