"""Tool catalog and per-agent tool permissions.

`Tool` rows mirror keys in the in-code TOOL_REGISTRY (app/tools/registry.py)
so permissions can be managed from the admin dashboard without redeploying.
`AgentTool` is the join table: an agent only gets the tools explicitly
enabled for it here -- see app/agents/resolver.py::get_allowed_tools.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Tool(Base):
    __tablename__ = "tools"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tool_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentTool(Base):
    __tablename__ = "agent_tools"
    __table_args__ = (UniqueConstraint("agent_id", "tool_id", name="uq_agent_tool"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    tool_id: Mapped[int] = mapped_column(ForeignKey("tools.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
