from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.api.deps import Principal, get_admin_principal
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.customer import Customer
from app.models.lead import Lead
from app.models.session import Session as SessionModel

router = APIRouter(prefix="/api/admin/customers", tags=["admin-customers"])


@router.get("")
def list_customers(
    limit: int = 100, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    query = db.query(Customer)
    if not principal.is_platform_admin:
        # A Customer row (an end-visitor contact) isn't owned directly --
        # it's reached only through the sessions it has with an agent.
        # Scope to visitors who have talked to at least one of this
        # user's own agents, via a distinct join rather than touching the
        # Customer table's shape.
        query = (
            query.join(SessionModel, SessionModel.customer_id == Customer.id)
            .join(Agent, Agent.id == SessionModel.agent_id)
            .filter(Agent.owner_user_id == principal.user_id)
            .distinct()
        )
    customers = query.order_by(Customer.created_at.desc()).limit(limit).all()
    out = []
    for c in customers:
        session_count_q = db.query(func.count(SessionModel.id)).filter(SessionModel.customer_id == c.id)
        lead_count_q = db.query(func.count(Lead.id)).filter(Lead.customer_id == c.id)
        if not principal.is_platform_admin:
            # The same visitor may also have talked to a *different*
            # tenant's agent (Customer rows aren't tenant-scoped). Don't
            # let a customer's counts here leak another tenant's session
            # or lead volume for that shared contact.
            session_count_q = session_count_q.join(Agent, Agent.id == SessionModel.agent_id).filter(
                Agent.owner_user_id == principal.user_id
            )
            lead_count_q = lead_count_q.join(Agent, Agent.id == Lead.agent_id).filter(
                Agent.owner_user_id == principal.user_id
            )
        session_count = session_count_q.scalar() or 0
        lead_count = lead_count_q.scalar() or 0
        out.append(
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "session_count": session_count,
                "lead_count": lead_count,
                "created_at": c.created_at,
            }
        )
    return out
