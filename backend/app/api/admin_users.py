"""Platform-operator management of self-serve customer accounts (app
User rows -- see app/models/user.py). There's no payment processor wired
up, so moving a customer off the free plan today is this: a human
operator reviews a request and flips it here. Swapping in real billing
later means a webhook handler calling the same `User.plan = ...` write,
not a change to this router's shape.

Deliberately `require_admin` only (the shared platform-operator secret),
never reachable by a customer's own session -- a customer cannot
upgrade themselves."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.api.deps import require_admin
from app.billing.plans import VALID_PLANS, get_plan_limits
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.user import User

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"], dependencies=[Depends(require_admin)])


class PlanUpdate(BaseModel):
    plan: str


@router.get("")
def list_users(limit: int = 200, db: DBSession = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).limit(limit).all()
    out = []
    for u in users:
        agent_count = db.query(func.count(Agent.id)).filter(Agent.owner_user_id == u.id).scalar() or 0
        out.append(
            {
                "id": u.id, "email": u.email, "name": u.name, "company_name": u.company_name,
                "plan": u.plan, "is_active": u.is_active, "agent_count": agent_count, "created_at": u.created_at,
            }
        )
    return out


@router.patch("/{user_id}/plan")
def update_user_plan(user_id: int, payload: PlanUpdate, db: DBSession = Depends(get_db)):
    if payload.plan not in VALID_PLANS:
        raise HTTPException(status_code=400, detail=f"Unknown plan '{payload.plan}'. Valid plans: {', '.join(sorted(VALID_PLANS))}.")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    user.plan = payload.plan
    db.commit()
    db.refresh(user)

    limits = get_plan_limits(user.plan)
    return {
        "id": user.id, "email": user.email, "plan": user.plan,
        "max_documents_per_agent": limits["max_documents_per_agent"],
        "max_file_size_mb": limits["max_file_size_bytes"] / (1024 * 1024),
    }
