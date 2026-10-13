"""Self-serve customer signup/login -- a completely separate trust
boundary from the platform-operator admin login (app/api/admin_auth.py).
A session token issued here only ever grants access to the one user's own
agents (see app/api/builder.py / app/api/deps.py::get_current_user), never
to anything under /api/admin/*."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database.connection import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas import AuthResponse, LoginRequest, SignupRequest, UserOut
from app.security.passwords import hash_password, verify_password
from app.security.tokens import generate_session_token, hash_token

logger = logging.getLogger("agent_platform.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _issue_session(db: DBSession, user: User) -> str:
    settings = get_settings()
    token = generate_session_token()
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.utcnow() + timedelta(hours=settings.USER_SESSION_TTL_HOURS),
        )
    )
    db.commit()
    return token


@router.post("/signup", response_model=AuthResponse, status_code=201)
def signup(payload: SignupRequest, db: DBSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    user = User(
        email=payload.email.lower().strip(),
        password_hash=hash_password(payload.password),
        name=payload.name.strip(),
        company_name=(payload.company_name or "").strip() or None,
    )
    db.add(user)
    db.flush()
    token = _issue_session(db, user)
    logger.info("user signed up user_id=%s", user.id)
    return AuthResponse(session_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: DBSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = _issue_session(db, user)
    logger.info("user logged in user_id=%s", user.id)
    return AuthResponse(session_token=token, user=UserOut.model_validate(user))


@router.post("/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),  # validates the token before we act on it
):
    """Deletes this one session row so the token stops working
    immediately, rather than waiting out its TTL."""
    token = authorization.split(" ", 1)[1].strip()  # get_current_user already validated this shape
    db.query(UserSession).filter(UserSession.token_hash == hash_token(token)).delete()
    db.commit()
    return None


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)
