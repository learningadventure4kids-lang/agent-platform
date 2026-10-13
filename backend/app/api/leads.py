from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.api.deps import Principal, get_admin_principal
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.lead import Lead
from app.schemas import LeadOut, LeadStatsOut, LeadUpdate

router = APIRouter(prefix="/api/admin/leads", tags=["admin-leads"])


def _scope_to_owned_agents(query, db: DBSession, principal: Principal):
    if principal.is_platform_admin:
        return query
    return query.join(Agent, Agent.id == Lead.agent_id).filter(Agent.owner_user_id == principal.user_id)


def _get_lead_scoped(db: DBSession, principal: Principal, lead_id: int) -> Lead:
    query = _scope_to_owned_agents(db.query(Lead).filter(Lead.id == lead_id), db, principal)
    lead = query.first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.get("", response_model=list[LeadOut])
def list_leads(
    agent_id: int | None = None, status: str | None = None,
    db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal),
):
    query = db.query(Lead)
    if agent_id is not None:
        query = query.filter(Lead.agent_id == agent_id)
    if status:
        query = query.filter(Lead.status == status)
    query = _scope_to_owned_agents(query, db, principal)
    return query.order_by(Lead.created_at.desc()).all()


@router.get("/stats", response_model=LeadStatsOut)
def lead_stats(
    agent_id: int | None = None, db: DBSession = Depends(get_db),
    principal: Principal = Depends(get_admin_principal),
):
    query = db.query(Lead)
    if agent_id is not None:
        query = query.filter(Lead.agent_id == agent_id)
    query = _scope_to_owned_agents(query, db, principal)
    leads = query.all()
    return LeadStatsOut(
        total=len(leads),
        new=sum(1 for l in leads if l.status == "new"),
        qualified=sum(1 for l in leads if l.status == "qualified"),
        contacted=sum(1 for l in leads if l.status == "contacted"),
        converted=sum(1 for l in leads if l.status == "converted"),
    )


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(
    lead_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    return _get_lead_scoped(db, principal, lead_id)


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: int, payload: LeadUpdate,
    db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal),
):
    lead = _get_lead_scoped(db, principal, lead_id)
    if payload.status is not None:
        lead.status = payload.status
    if payload.notes is not None:
        lead.metadata_json = {**lead.metadata_json, "admin_notes": payload.notes}
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}/conversation")
def get_lead_conversation(
    lead_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    from app.models.message import Message

    lead = _get_lead_scoped(db, principal, lead_id)
    if not lead.session_id:
        return {"messages": []}
    messages = (
        db.query(Message)
        .filter(Message.session_id == lead.session_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return {"messages": [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]}
