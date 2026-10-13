"""Each agent gets exactly one auto-created "default" knowledge base today
(see app/models/knowledge_base.py docstring for why the schema still
allows more than one later)."""
from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.models.agent import Agent
from app.models.knowledge_base import KnowledgeBase


def get_or_create_default(db: DBSession, agent: Agent) -> KnowledgeBase:
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.agent_id == agent.id).first()
    if kb:
        return kb
    kb = KnowledgeBase(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        name=f"{agent.brand_name} knowledge base",
    )
    db.add(kb)
    db.flush()
    return kb


def get_for_agent(db: DBSession, agent_id: int) -> KnowledgeBase | None:
    return db.query(KnowledgeBase).filter(KnowledgeBase.agent_id == agent_id).first()
