"""Thin data-access layer over the `agents` table -- the live agent
registry. (Sample agent *definitions* used to seed the database live in
app/seed.py; this module only ever reads/writes the database, which is the
actual source of truth at runtime.)"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.models.agent import Agent
from app.models.tool import AgentTool, Tool


def get_agent_by_id(db: DBSession, agent_id: int) -> Optional[Agent]:
    return db.query(Agent).filter(Agent.id == agent_id).first()


def get_agent_by_key(db: DBSession, agent_key: str) -> Optional[Agent]:
    return db.query(Agent).filter(Agent.agent_key == agent_key).first()


def get_agent_by_token_hash(db: DBSession, token_hash: str) -> Optional[Agent]:
    return db.query(Agent).filter(Agent.public_token_hash == token_hash).first()


def list_agents(db: DBSession) -> list[Agent]:
    return db.query(Agent).order_by(Agent.created_at.asc()).all()


def get_allowed_tool_keys(db: DBSession, agent_id: int) -> list[str]:
    rows = (
        db.query(Tool.tool_key)
        .join(AgentTool, AgentTool.tool_id == Tool.id)
        .filter(AgentTool.agent_id == agent_id, AgentTool.enabled.is_(True), Tool.enabled.is_(True))
        .all()
    )
    return [r[0] for r in rows]


def set_agent_tools(db: DBSession, agent_id: int, tool_keys: list[str]) -> None:
    """Replaces the agent's tool permissions with exactly `tool_keys`."""
    db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()
    db.flush()
    for key in tool_keys:
        tool = db.query(Tool).filter(Tool.tool_key == key).first()
        if not tool:
            continue
        db.add(AgentTool(agent_id=agent_id, tool_id=tool.id, enabled=True))
    db.flush()
