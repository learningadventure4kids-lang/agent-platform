from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from app.agents.registry import get_agent_by_id
from app.agents.resolver import resolve_agent
from app.database.connection import get_db
from app.schemas import AgentPublicInfo, CreateSessionRequest, MessageOut, SessionStateOut
from app.security.domains import is_origin_allowed
from app.services import session_service

router = APIRouter(prefix="/api/session", tags=["session"])

RETURNING_VISITOR_GAP = timedelta(seconds=120)


def _agent_public(agent) -> AgentPublicInfo:
    return AgentPublicInfo(
        name=agent.name,
        brand=agent.brand_name,
        welcome_message=agent.welcome_message,
        suggestions=agent.suggestions,
        theme=agent.theme,
    )


@router.post("", response_model=SessionStateOut)
def create_session(payload: CreateSessionRequest, request: Request, db: DBSession = Depends(get_db)):
    agent = resolve_agent(db, payload.agent_token, request)
    session = session_service.create_session(db, agent.id)
    db.commit()
    return SessionStateOut(
        session_id=session.session_id,
        agent=_agent_public(agent),
        conversation_status=session.conversation_status,
        is_returning=False,
        messages=[],
    )


@router.get("/{session_id}", response_model=SessionStateOut)
def get_session(session_id: str, request: Request, db: DBSession = Depends(get_db)):
    session = session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    agent = get_agent_by_id(db, session.agent_id)
    if not agent or not agent.enabled:
        raise HTTPException(status_code=404, detail="Session not found")
    if not is_origin_allowed(agent.allowed_domains, request):
        raise HTTPException(status_code=403, detail="Not permitted on this domain.")

    existing_messages = session_service.get_messages(db, session_id)
    gap = datetime.utcnow() - session.last_activity_at
    is_returning = bool(existing_messages) and gap > RETURNING_VISITOR_GAP

    session_service.touch_session(db, session)
    db.commit()

    return SessionStateOut(
        session_id=session.session_id,
        agent=_agent_public(agent),
        conversation_status=session.conversation_status,
        is_returning=is_returning,
        messages=[MessageOut.model_validate(m) for m in existing_messages],
    )


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def get_session_messages(session_id: str, db: DBSession = Depends(get_db)):
    session = session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return [MessageOut.model_validate(m) for m in session_service.get_messages(db, session_id)]


@router.delete("/{session_id}")
def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    """Deletes the session and its messages only. Leads/consultations
    already created are preserved."""
    session = session_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    from app.models.message import Message

    db.query(Message).filter(Message.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"deleted": True, "session_id": session_id}
