"""Bearer-token sessions for self-serve customer users (app/api/user_auth.py,
app/api/deps.py::get_current_user). Mirrors the agent public-token pattern
deliberately: only an HMAC hash of the session token is ever stored (see
app/security/tokens.py, reused here), so a leaked database dump cannot be
replayed as a working session, and the plaintext token is only ever seen
once, in the signup/login response body."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
