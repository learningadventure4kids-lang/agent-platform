"""Turns a public agent_token into a validated, enabled Agent row. This is
the single choke point every chat/session request passes through -- see
app/api/chat.py."""
from __future__ import annotations

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.agents.registry import get_agent_by_token_hash
from app.models.agent import Agent
from app.security.domains import is_origin_allowed
from app.security.tokens import hash_token


class AgentResolutionError(HTTPException):
    pass


def resolve_agent(db: DBSession, agent_token: str, request: Request | None = None) -> Agent:
    if not agent_token:
        raise AgentResolutionError(status.HTTP_401_UNAUTHORIZED, "Missing agent_token.")

    token_hash = hash_token(agent_token)
    agent = get_agent_by_token_hash(db, token_hash)

    if not agent:
        raise AgentResolutionError(status.HTTP_401_UNAUTHORIZED, "Invalid agent token.")
    if not agent.enabled:
        raise AgentResolutionError(status.HTTP_403_FORBIDDEN, "This agent is currently disabled.")

    if request is not None and not is_origin_allowed(agent.allowed_domains, request):
        raise AgentResolutionError(
            status.HTTP_403_FORBIDDEN, "This agent is not permitted to run on this domain."
        )

    return agent
