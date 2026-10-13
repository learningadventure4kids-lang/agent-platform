from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.agents.registry import get_allowed_tool_keys, set_agent_tools
from app.api.deps import Principal, get_admin_principal
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.tool import Tool
from app.schemas import AgentToolOut, AgentToolsUpdate, ToolExecutionLogOut, ToolOut
from app.tools.registry import get_tool_metadata

router = APIRouter(prefix="/api/admin", tags=["admin-tools"])


def _get_agent_scoped(db: DBSession, principal: Principal, agent_id: int) -> Agent:
    query = db.query(Agent).filter(Agent.id == agent_id)
    if not principal.is_platform_admin:
        query = query.filter(Agent.owner_user_id == principal.user_id)
    agent = query.first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _enrich(t: Tool) -> dict:
    meta = get_tool_metadata(t.tool_key) or {}
    return {
        "id": t.id, "tool_key": t.tool_key, "name": t.name, "description": t.description,
        "enabled": t.enabled,
        "category": meta.get("category"),
        "requires_confirmation": meta.get("requires_confirmation"),
        "risk_level": meta.get("risk_level"),
        "timeout_seconds": meta.get("timeout_seconds"),
    }


@router.get("/tools", response_model=list[ToolOut])
def list_tools(db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)):
    # The tool catalog itself is platform-wide (every tool type that
    # exists, regardless of who it's granted to) -- any authenticated
    # principal, admin or customer, can read it. Only *grants* on a
    # specific agent are ownership-scoped, below.
    tools = db.query(Tool).order_by(Tool.tool_key.asc()).all()
    return [ToolOut(**_enrich(t)) for t in tools]


@router.get("/agents/{agent_id}/tools", response_model=list[AgentToolOut])
def get_agent_tools(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    _get_agent_scoped(db, principal, agent_id)
    granted = set(get_allowed_tool_keys(db, agent_id))
    tools = db.query(Tool).order_by(Tool.tool_key.asc()).all()
    return [
        AgentToolOut(**_enrich(t), granted=t.tool_key in granted)
        for t in tools
    ]


@router.put("/agents/{agent_id}/tools", response_model=list[AgentToolOut])
def update_agent_tools(
    agent_id: int, payload: AgentToolsUpdate,
    db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal),
):
    _get_agent_scoped(db, principal, agent_id)
    set_agent_tools(db, agent_id, payload.tool_keys)
    db.commit()
    return get_agent_tools(agent_id, db, principal)


@router.get("/agents/{agent_id}/tool-executions", response_model=list[ToolExecutionLogOut])
def get_agent_tool_executions(
    agent_id: int, limit: int = 100,
    db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal),
):
    """Read-only audit trail of every tool call the orchestration graph has
    made for this agent -- success, denied (e.g. a confirmation-required
    tool called without confirmation), error, or timeout. Never includes
    raw arguments/results; both are sanitized before being written (see
    app/services/tool_audit_service.py)."""
    from app.models.tool_execution_log import ToolExecutionLog

    _get_agent_scoped(db, principal, agent_id)
    rows = (
        db.query(ToolExecutionLog)
        .filter(ToolExecutionLog.agent_id == agent_id)
        .order_by(ToolExecutionLog.started_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    return rows
