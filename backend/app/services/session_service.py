"""Session + message persistence, scoped to a single agent. This is what
makes the widget "remember" a visitor: everything is read back from the
database, never kept only in server memory or only in the browser."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.models.message import Message
from app.models.session import Session as SessionModel


def create_session(db: DBSession, agent_id: int) -> SessionModel:
    session = SessionModel(agent_id=agent_id)
    db.add(session)
    db.flush()
    return session


def get_session(db: DBSession, session_id: str) -> Optional[SessionModel]:
    return db.query(SessionModel).filter(SessionModel.session_id == session_id).first()


def get_or_create_session(
    db: DBSession, agent_id: int, session_id: Optional[str]
) -> tuple[SessionModel, bool]:
    """Returns (session, is_new). If session_id belongs to a *different*
    agent than agent_id, a fresh session is created instead of reused --
    sessions must never be shared across tenants."""
    if session_id:
        existing = get_session(db, session_id)
        if existing and existing.agent_id == agent_id:
            return existing, False
    return create_session(db, agent_id), True


def save_message(db: DBSession, session_id: str, role: str, content: str) -> Message:
    msg = Message(session_id=session_id, role=role, content=content)
    db.add(msg)
    db.flush()
    return msg


def get_messages(db: DBSession, session_id: str, limit: int = 200) -> list[Message]:
    return (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )


def touch_session(db: DBSession, session: SessionModel) -> None:
    session.last_activity_at = datetime.utcnow()
    db.flush()


def update_metadata(db: DBSession, session: SessionModel, **updates) -> None:
    session.session_metadata = {**session.session_metadata, **updates}
    db.flush()
