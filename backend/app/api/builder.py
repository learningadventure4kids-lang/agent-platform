"""The self-serve agent builder: a logged-in customer's own "create an
agent from a persona, upload documents, get an embed script" flow.
Completely separate from app/api/admin_agents.py (the platform-operator
dashboard) -- every route here is scoped to `Depends(get_current_user)`,
and every query additionally filters on `Agent.owner_user_id == user.id`
so one customer can never see or touch another's agent, even by guessing
an id (a mismatch is a 404, not a 403, so existence isn't leaked either).
"""
from __future__ import annotations

import logging
import re
import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.agents.personas import get_persona, list_personas
from app.agents.registry import get_allowed_tool_keys, set_agent_tools
from app.api.chat import run_chat_turn
from app.api.deps import get_current_user
from app.billing.plans import get_plan_limits
from app.config import get_settings
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.message import Message
from app.models.session import Session as SessionModel
from app.models.tool import AgentTool, Tool
from app.models.tool_execution_log import ToolExecutionLog
from app.models.user import User
from app.schemas import (
    AgentToolOut,
    AgentToolsUpdate,
    BuilderAgentCreate,
    BuilderAgentOut,
    BuilderAgentUpdate,
    ChatResponse,
    EmbedSnippetOut,
    LeadOut,
    LeadStatsOut,
    LeadUpdate,
    PersonaOut,
    PreviewChatRequest,
    ToolExecutionLogOut,
    ToolOut,
)
from app.security.file_storage import FileValidationError
from app.security.tokens import generate_token, hash_token
from app.services.document_upload_service import ingest_uploaded_document
from app.tools.registry import get_tool_metadata

logger = logging.getLogger("agent_platform.builder")

router = APIRouter(prefix="/api/builder", tags=["builder"])

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return slug or "agent"


def _require_owned_agent(db: DBSession, user: User, agent_id: int) -> Agent:
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.owner_user_id == user.id)
        .first()
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _owned_agent_ids(db: DBSession, user: User) -> list[int]:
    rows = db.query(Agent.id).filter(Agent.owner_user_id == user.id).all()
    return [r[0] for r in rows]


def _to_out(db: DBSession, agent: Agent) -> BuilderAgentOut:
    tool_count = db.query(func.count(AgentTool.id)).filter(
        AgentTool.agent_id == agent.id, AgentTool.enabled.is_(True)
    ).scalar() or 0
    session_count = db.query(func.count(SessionModel.id)).filter(
        SessionModel.agent_id == agent.id
    ).scalar() or 0
    lead_count = db.query(func.count(Lead.id)).filter(Lead.agent_id == agent.id).scalar() or 0
    return BuilderAgentOut(
        id=agent.id,
        agent_key=agent.agent_key,
        persona_key=(agent.theme or {}).get("persona_key"),
        name=agent.name,
        brand_name=agent.brand_name,
        welcome_message=agent.welcome_message,
        suggestions=agent.suggestions,
        system_prompt=agent.system_prompt,
        allowed_domains=agent.allowed_domains,
        theme=agent.theme,
        enabled=agent.enabled,
        created_at=agent.created_at,
        tool_count=tool_count,
        session_count=session_count,
        lead_count=lead_count,
    )


def _build_embed_snippet(agent: Agent, public_token: str) -> EmbedSnippetOut:
    """The widget (widget/src/index.tsx) can figure out its own API URL at
    runtime -- it reads `document.currentScript.src` (only reliable at the
    moment this very `<script src="...">` tag first runs) and uses that
    tag's own origin, since the widget bundle and the API it talks to are
    normally served from the same place. So the snippet below leaves
    `apiUrl` out whenever that's true, which is the common case and the
    whole point of this: a customer pasting the snippet shouldn't have to
    know or care what the API's URL is.

    It's only included explicitly when `PUBLIC_WIDGET_SCRIPT_URL` and
    `PUBLIC_API_BASE_URL` have different origins -- e.g. the widget script
    is served from a CDN but the API lives elsewhere (see the README's
    production notes on this) -- because auto-detection would then infer
    the CDN's origin, not the API's, and silently point the widget at the
    wrong place."""
    settings = get_settings()
    script_tag = f'<script src="{settings.PUBLIC_WIDGET_SCRIPT_URL}"></script>'

    same_origin = urlsplit(settings.PUBLIC_WIDGET_SCRIPT_URL)[:2] == urlsplit(settings.PUBLIC_API_BASE_URL)[:2]
    api_url_line = "" if same_origin else f'    apiUrl: "{settings.PUBLIC_API_BASE_URL}",\n'

    install_snippet = (
        f"{script_tag}\n"
        "<script>\n"
        "  AriaWidget.mountFloating({\n"
        f'    agentToken: "{public_token}",\n'
        f"{api_url_line}"
        "  });\n"
        "</script>"
    )
    return EmbedSnippetOut(
        agent_id=agent.id, public_token=public_token, script_tag=script_tag, install_snippet=install_snippet,
    )


@router.get("/personas", response_model=list[PersonaOut])
def personas():
    return [PersonaOut(**p) for p in list_personas()]


@router.get("/agents", response_model=list[BuilderAgentOut])
def list_my_agents(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    agents = (
        db.query(Agent)
        .filter(Agent.owner_user_id == user.id)
        .order_by(Agent.created_at.desc())
        .all()
    )
    return [_to_out(db, a) for a in agents]


@router.get("/agents/{agent_id}", response_model=BuilderAgentOut)
def get_my_agent(agent_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    return _to_out(db, _require_owned_agent(db, user, agent_id))


@router.post("/agents", response_model=EmbedSnippetOut, status_code=201)
def create_my_agent(
    payload: BuilderAgentCreate, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)
):
    persona = get_persona(payload.persona_key)
    if persona is None:
        raise HTTPException(status_code=400, detail=f"Unknown persona_key '{payload.persona_key}'")

    # agent_key must be globally unique (it's the slug used in logs/seed
    # data too) -- scope it to this user and brand, with a short random
    # suffix so two agents with the same brand name never collide.
    base_slug = _slugify(payload.brand_name)
    agent_key = f"{base_slug}-{user.id}-{secrets.token_hex(3)}"
    tenant_id = f"user-{user.id}"

    token = generate_token()
    agent = Agent(
        agent_key=agent_key,
        tenant_id=tenant_id,
        owner_user_id=user.id,
        public_token_hash=hash_token(token),
        name=payload.name,
        brand_name=payload.brand_name,
        system_prompt=persona["system_prompt"],
        welcome_message=payload.welcome_message or persona["welcome_message"],
        suggestions=list(persona["suggestions"]),
        lead_fields=["name", "email", "phone"],
        theme={"persona_key": persona["key"], **({"accent_color": payload.accent_color} if payload.accent_color else {})},
        enabled=True,
    )
    db.add(agent)
    db.flush()
    set_agent_tools(db, agent.id, persona["tool_keys"])
    db.commit()
    db.refresh(agent)

    logger.info("self-serve agent created agent_id=%s user_id=%s persona=%s", agent.id, user.id, persona["key"])
    return _build_embed_snippet(agent, token)


@router.patch("/agents/{agent_id}", response_model=BuilderAgentOut)
def update_my_agent(
    agent_id: int, payload: BuilderAgentUpdate,
    db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    agent = _require_owned_agent(db, user, agent_id)
    data = payload.model_dump(exclude_unset=True)
    accent_color = data.pop("accent_color", None)
    for field, value in data.items():
        setattr(agent, field, value)
    if accent_color is not None:
        agent.theme = {**(agent.theme or {}), "accent_color": accent_color}
    db.commit()
    db.refresh(agent)
    return _to_out(db, agent)


@router.post("/agents/{agent_id}/rotate-token", response_model=EmbedSnippetOut)
def rotate_my_agent_token(agent_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    agent = _require_owned_agent(db, user, agent_id)
    token = generate_token()
    agent.public_token_hash = hash_token(token)
    db.commit()
    return _build_embed_snippet(agent, token)


@router.delete("/agents/{agent_id}")
def delete_my_agent(agent_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    agent = _require_owned_agent(db, user, agent_id)
    db.query(AgentTool).filter(AgentTool.agent_id == agent_id).delete()
    db.delete(agent)
    db.commit()
    return {"deleted": True, "agent_id": agent_id}


# --- Tools (global catalog is read-only reference data, safe for any
# logged-in customer to see; grants and the execution log are per-agent
# and therefore ownership-scoped like everything else in this file) ---

def _enrich_tool(t: Tool) -> dict:
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
def list_tool_catalog(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    tools = db.query(Tool).order_by(Tool.tool_key.asc()).all()
    return [ToolOut(**_enrich_tool(t)) for t in tools]


@router.get("/agents/{agent_id}/tools", response_model=list[AgentToolOut])
def get_my_agent_tools(agent_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    agent = _require_owned_agent(db, user, agent_id)
    granted = set(get_allowed_tool_keys(db, agent.id))
    tools = db.query(Tool).order_by(Tool.tool_key.asc()).all()
    return [AgentToolOut(**_enrich_tool(t), granted=t.tool_key in granted) for t in tools]


@router.put("/agents/{agent_id}/tools", response_model=list[AgentToolOut])
def update_my_agent_tools(
    agent_id: int, payload: AgentToolsUpdate, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    agent = _require_owned_agent(db, user, agent_id)
    set_agent_tools(db, agent.id, payload.tool_keys)
    db.commit()
    return get_my_agent_tools(agent_id, db, user)


@router.get("/agents/{agent_id}/tool-executions", response_model=list[ToolExecutionLogOut])
def get_my_agent_tool_executions(
    agent_id: int, limit: int = 100, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    agent = _require_owned_agent(db, user, agent_id)
    rows = (
        db.query(ToolExecutionLog)
        .filter(ToolExecutionLog.agent_id == agent.id)
        .order_by(ToolExecutionLog.started_at.desc())
        .limit(min(limit, 500))
        .all()
    )
    return rows


@router.get("/customers")
def list_my_customers(db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Unlike the platform-admin version of this endpoint (which matches a
    `Customer` row globally across every tenant's agents by email/phone --
    see app/api/admin_customers.py), this one only ever surfaces a customer
    who has a session or a lead against one of *this user's own* agents,
    and counts are computed from that scoped set alone. A customer who
    separately also talked to someone else's agent must never have that
    activity (or even their existence) visible here -- that would be a
    cross-tenant data leak through a shared identity table."""
    owned_ids = _owned_agent_ids(db, user)
    if not owned_ids:
        return []

    customer_ids = {
        row[0] for row in db.query(SessionModel.customer_id)
        .filter(SessionModel.agent_id.in_(owned_ids), SessionModel.customer_id.isnot(None))
        .distinct()
        .all()
    }
    customer_ids |= {
        row[0] for row in db.query(Lead.customer_id)
        .filter(Lead.agent_id.in_(owned_ids), Lead.customer_id.isnot(None))
        .distinct()
        .all()
    }
    if not customer_ids:
        return []

    customers = db.query(Customer).filter(Customer.id.in_(customer_ids)).order_by(Customer.created_at.desc()).all()
    out = []
    for c in customers:
        session_count = db.query(func.count(SessionModel.id)).filter(
            SessionModel.customer_id == c.id, SessionModel.agent_id.in_(owned_ids),
        ).scalar() or 0
        lead_count = db.query(func.count(Lead.id)).filter(
            Lead.customer_id == c.id, Lead.agent_id.in_(owned_ids),
        ).scalar() or 0
        out.append(
            {
                "id": c.id, "name": c.name, "email": c.email, "phone": c.phone,
                "session_count": session_count, "lead_count": lead_count, "created_at": c.created_at,
            }
        )
    return out


@router.post("/agents/{agent_id}/documents")
async def upload_my_agent_document(
    agent_id: int, file: UploadFile = File(...),
    db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    from app.models.document import Document

    agent = _require_owned_agent(db, user, agent_id)
    limits = get_plan_limits(user.plan)

    existing_count = db.query(func.count(Document.id)).filter(Document.agent_id == agent.id).scalar() or 0
    if existing_count >= limits["max_documents_per_agent"]:
        raise HTTPException(
            status_code=403,
            detail=(
                f"You've reached the {limits['max_documents_per_agent']}-document limit for this agent "
                f"on the {user.plan.capitalize()} plan. Upgrade to Plus for more."
            ),
        )

    contents = await file.read()
    try:
        result = ingest_uploaded_document(
            db, agent, file.filename or "upload", contents, max_file_size=limits["max_file_size_bytes"]
        )
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.get("/me/plan")
def get_my_plan(user: User = Depends(get_current_user)):
    """What the logged-in customer's current plan allows -- the frontend
    uses this to show remaining document quota and to disable the upload
    button before a doomed request round-trips to the server."""
    limits = get_plan_limits(user.plan)
    return {
        "plan": user.plan,
        "max_documents_per_agent": limits["max_documents_per_agent"],
        "max_file_size_mb": limits["max_file_size_bytes"] / (1024 * 1024),
    }


@router.post("/agents/{agent_id}/preview-chat", response_model=ChatResponse)
def preview_chat(
    agent_id: int, payload: PreviewChatRequest, request: Request,
    db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """Lets a customer try their own agent from inside the dashboard, so
    they can see what a visitor would experience before pasting the embed
    script anywhere. Authenticated by the customer's own session + agent
    ownership (`_require_owned_agent`) rather than the public `agent_token`
    -- the plaintext token is only ever shown once at creation/rotation, so
    requiring it here would make the preview unusable most of the time.
    Runs the exact same `run_chat_turn` pipeline as the public widget
    (same LangGraph agent, same tools, same rate limiting), so this is a
    real conversation (and a real session, visible in the dashboard's
    session list), not a mock of one."""
    agent = _require_owned_agent(db, user, agent_id)
    return run_chat_turn(db, agent, request, payload.session_id, payload.message)


@router.get("/sessions")
def list_my_sessions(
    agent_id: int | None = None, limit: int = 100,
    db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    """The same session list the admin dashboard shows, but scoped to this
    customer's own agents -- an owned `agent_id` narrows it further, but an
    agent_id that isn't theirs simply yields no rows (never a 404) since
    this is a filtered list, not a lookup by id."""
    owned_ids = _owned_agent_ids(db, user)
    if not owned_ids:
        return []
    query = db.query(SessionModel).filter(SessionModel.agent_id.in_(owned_ids))
    if agent_id is not None:
        query = query.filter(SessionModel.agent_id == agent_id)
    sessions = query.order_by(SessionModel.last_activity_at.desc()).limit(limit).all()

    out = []
    for s in sessions:
        agent = db.query(Agent).filter(Agent.id == s.agent_id).first()
        customer = db.query(Customer).filter(Customer.id == s.customer_id).first() if s.customer_id else None
        message_count = db.query(func.count(Message.id)).filter(Message.session_id == s.session_id).scalar() or 0
        out.append(
            {
                "session_id": s.session_id,
                "agent_id": s.agent_id,
                "agent_key": agent.agent_key if agent else None,
                "agent_brand": agent.brand_name if agent else None,
                "customer_name": customer.name if customer else None,
                "customer_contact": (customer.email or customer.phone) if customer else None,
                "conversation_status": s.conversation_status,
                "message_count": message_count,
                "created_at": s.created_at,
                "last_activity_at": s.last_activity_at,
            }
        )
    return out


@router.get("/leads/stats", response_model=LeadStatsOut)
def my_lead_stats(
    agent_id: int | None = None, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    owned_ids = _owned_agent_ids(db, user)
    if not owned_ids:
        return LeadStatsOut(total=0, new=0, qualified=0, contacted=0, converted=0)
    query = db.query(Lead).filter(Lead.agent_id.in_(owned_ids))
    if agent_id is not None:
        query = query.filter(Lead.agent_id == agent_id)
    leads = query.all()
    return LeadStatsOut(
        total=len(leads),
        new=sum(1 for l in leads if l.status == "new"),
        qualified=sum(1 for l in leads if l.status == "qualified"),
        contacted=sum(1 for l in leads if l.status == "contacted"),
        converted=sum(1 for l in leads if l.status == "converted"),
    )


@router.get("/leads", response_model=list[LeadOut])
def list_my_leads(
    agent_id: int | None = None, status: str | None = None,
    db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    owned_ids = _owned_agent_ids(db, user)
    if not owned_ids:
        return []
    query = db.query(Lead).filter(Lead.agent_id.in_(owned_ids))
    if agent_id is not None:
        query = query.filter(Lead.agent_id == agent_id)
    if status:
        query = query.filter(Lead.status == status)
    return query.order_by(Lead.created_at.desc()).all()


def _require_owned_lead(db: DBSession, user: User, lead_id: int) -> Lead:
    owned_ids = _owned_agent_ids(db, user)
    lead = (
        db.query(Lead)
        .filter(Lead.id == lead_id, Lead.agent_id.in_(owned_ids or [-1]))
        .first()
    )
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_my_lead(lead_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    return _require_owned_lead(db, user, lead_id)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_my_lead(
    lead_id: int, payload: LeadUpdate, db: DBSession = Depends(get_db), user: User = Depends(get_current_user),
):
    lead = _require_owned_lead(db, user, lead_id)
    if payload.status is not None:
        lead.status = payload.status
    if payload.notes is not None:
        lead.metadata_json = {**lead.metadata_json, "admin_notes": payload.notes}
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/leads/{lead_id}/conversation")
def get_my_lead_conversation(lead_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    lead = _require_owned_lead(db, user, lead_id)
    if not lead.session_id:
        return {"messages": []}
    messages = (
        db.query(Message)
        .filter(Message.session_id == lead.session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return {"messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]}


@router.get("/agents/{agent_id}/documents")
def list_my_agent_documents(agent_id: int, db: DBSession = Depends(get_db), user: User = Depends(get_current_user)):
    from app.models.document import Document

    agent = _require_owned_agent(db, user, agent_id)
    docs = db.query(Document).filter(Document.agent_id == agent.id).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id, "original_filename": d.original_filename, "file_type": d.file_type,
            "status": d.status, "processing_error": d.processing_error, "chunk_count": d.chunk_count,
            "created_at": d.created_at,
        }
        for d in docs
    ]
