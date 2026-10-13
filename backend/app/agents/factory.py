"""Thin, backward-compatible entry point LangGraph code calls to get an
agent's chat model. All actual provider resolution (agent -> provider
config -> concrete provider -> LangChain chat model, with default-provider
and fallback-provider handling) lives in app/ai/resolution.py -- this
module exists so app/agents/graph.py's import/call site never needed to
change shape when provider configurability was added."""
from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.ai.resolution import resolve_chat_model
from app.models.agent import Agent


def get_llm(db: DBSession, agent: Agent):
    return resolve_chat_model(db, agent)
