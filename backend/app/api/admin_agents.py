"""Agent management for the admin screen. Reachable by two different
logins: the platform operator (sees and manages every agent) and a
self-serve customer (sees and manages only the agents they created --
see app/api/deps.py::Principal for how that's resolved and enforced).

Creating an agent returns its public token exactly once
(`AgentCreatedOut.public_token`) -- from then on only the hash is stored,
so if the admin loses the token, they must rotate it (which issues a new
one and invalidates the old) rather than "retrieve" it."""
from __future__ import annotations

import re
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.agents.registry import get_agent_by_key, list_agents, set_agent_tools
from app.api.deps import Principal, get_admin_principal
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.lead import Lead
from app.models.session import Session as SessionModel
from app.models.tool import AgentTool
from app.schemas import AgentCreate, AgentCreatedOut, AgentOut, AgentUpdate, TokenRotatedOut
from app.security.tokens import generate_token, hash_token

router = APIRouter(prefix="/api/admin/agents", tags=["admin-agents"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "agent"


def _get_agent_scoped(db: DBSession, principal: Principal, agent_id: int) -> Agent:
    """The one place every route here looks up an agent by id -- a
    platform-admin principal can reach any agent, a customer principal
    only their own (anything else is a 404, never a 403, so a customer
    probing ids never learns whether an agent they don't own exists)."""
    query = db.query(Agent).filter(Agent.id == agent_id)
    if not principal.is_platform_admin:
        query = query.filter(Agent.owner_user_id == principal.user_id)
    agent = query.first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _to_out(db: DBSession, agent: Agent) -> AgentOut:
    tool_count = db.query(func.count(AgentTool.id)).filter(
        AgentTool.agent_id == agent.id, AgentTool.enabled.is_(True)
    ).scalar() or 0
    session_count = db.query(func.count(SessionModel.id)).filter(
        SessionModel.agent_id == agent.id
    ).scalar() or 0
    lead_count = db.query(func.count(Lead.id)).filter(Lead.agent_id == agent.id).scalar() or 0

    return AgentOut(
        **{k: getattr(agent, k) for k in AgentOut.model_fields if hasattr(agent, k)},
        tool_count=tool_count,
        session_count=session_count,
        lead_count=lead_count,
    )


@router.get("", response_model=list[AgentOut])
def list_all_agents(db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)):
    agents = list_agents(db)
    if not principal.is_platform_admin:
        agents = [a for a in agents if a.owner_user_id == principal.user_id]
    return [_to_out(db, a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    return _to_out(db, _get_agent_scoped(db, principal, agent_id))


@router.post("", response_model=AgentCreatedOut)
def create_agent(
    payload: AgentCreate, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    # A self-serve customer's "New agent" form never hands the browser
    # control over agent_key/tenant_id/owner/provider -- those are either
    # derived here or simply not theirs to set, the same boundary
    # app/api/builder.py already enforces for the guided wizard. The
    # platform operator keeps full control over all of it, unchanged.
    if principal.is_platform_admin:
        agent_key = payload.agent_key
        tenant_id = payload.tenant_id or payload.agent_key
        owner_user_id = None
        provider_id = payload.provider_id
        fallback_provider_id = payload.fallback_provider_id
    else:
        base_slug = _slugify(payload.brand_name or payload.agent_key or "agent")
        agent_key = f"{base_slug}-{principal.user_id}-{secrets.token_hex(3)}"
        tenant_id = f"user-{principal.user_id}"
        owner_user_id = principal.user_id
        # AI Providers are platform-wide infrastructure the operator
        # configures (and pays for) -- a customer account never gets to
        # point their agent at an arbitrary provider_id by guessing one.
        provider_id = None
        fallback_provider_id = None

    if get_agent_by_key(db, agent_key):
        raise HTTPException(status_code=409, detail="agent_key already exists")

    token = generate_token()
    agent = Agent(
        agent_key=agent_key,
        tenant_id=tenant_id,
        owner_user_id=owner_user_id,
        public_token_hash=hash_token(token),
        name=payload.name,
        brand_name=payload.brand_name,
        description=payload.description,
        system_prompt=payload.system_prompt,
        welcome_message=payload.welcome_message,
        suggestions=payload.suggestions,
        lead_fields=payload.lead_fields,
        theme=payload.theme,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        enabled=payload.enabled,
        allowed_domains=payload.allowed_domains,
        provider_id=provider_id,
        fallback_provider_id=fallback_provider_id,
    )
    db.add(agent)
    db.flush()
    set_agent_tools(db, agent.id, payload.tool_keys)
    db.commit()
    db.refresh(agent)

    out = _to_out(db, agent)
    return AgentCreatedOut(**out.model_dump(), public_token=token)


@router.put("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: int, payload: AgentUpdate,
    db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal),
):
    agent = _get_agent_scoped(db, principal, agent_id)

    data = payload.model_dump(exclude_unset=True)
    if not principal.is_platform_admin:
        # Same "providers are admin-only infrastructure" boundary as
        # creation -- a customer editing their own agent can't repoint it
        # at a different provider_id even if the field is present in the
        # request body.
        data.pop("provider_id", None)
        data.pop("fallback_provider_id", None)
    for field, value in data.items():
        setattr(agent, field, value)

    db.commit()
    db.refresh(agent)
    return _to_out(db, agent)


@router.delete("/{agent_id}")
def delete_agent(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    agent = _get_agent_scoped(db, principal, agent_id)
    db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()
    db.delete(agent)
    db.commit()
    return {"deleted": True, "agent_id": agent_id}


@router.post("/{agent_id}/rotate-token", response_model=TokenRotatedOut)
def rotate_token(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    agent = _get_agent_scoped(db, principal, agent_id)
    new_token = generate_token()
    agent.public_token_hash = hash_token(new_token)
    db.commit()
    return TokenRotatedOut(agent_id=agent.id, public_token=new_token)


@router.post("/{agent_id}/disable", response_model=AgentOut)
def disable_agent(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    agent = _get_agent_scoped(db, principal, agent_id)
    agent.enabled = False
    db.commit()
    db.refresh(agent)
    return _to_out(db, agent)


@router.post("/{agent_id}/enable", response_model=AgentOut)
def enable_agent(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    agent = _get_agent_scoped(db, principal, agent_id)
    agent.enabled = True
    db.commit()
    db.refresh(agent)
    return _to_out(db, agent)
