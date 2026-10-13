from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.api.deps import Principal, get_admin_principal
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.customer import Customer
from app.models.message import Message
from app.models.session import Session as SessionModel

router = APIRouter(prefix="/api/admin/sessions", tags=["admin-sessions"])


@router.get("")
def list_sessions(
    agent_id: int | None = None, limit: int = 100,
    db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal),
):
    query = db.query(SessionModel)
    if agent_id is not None:
        if not principal.is_platform_admin:
            owned = db.query(Agent.id).filter(
                Agent.id == agent_id, Agent.owner_user_id == principal.user_id
            ).first()
            if not owned:
                raise HTTPException(status_code=404, detail="Agent not found")
        query = query.filter(SessionModel.agent_id == agent_id)
    elif not principal.is_platform_admin:
        query = query.join(Agent, Agent.id == SessionModel.agent_id).filter(
            Agent.owner_user_id == principal.user_id
        )
    sessions = query.order_by(SessionModel.last_activity_at.desc()).limit(limit).all()

    out = []
    for s in sessions:
        agent = db.query(Agent).filter(Agent.id == s.agent_id).first()
        customer = db.query(Customer).filter(Customer.id == s.customer_id).first() if s.customer_id else None
        message_count = db.query(func.count(Message.id)).filter(Message.session_id == s.session_id).scalar() or 0
        out.append(
            {
                "session_id": s.session_id,
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
