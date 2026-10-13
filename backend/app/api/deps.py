"""Shared FastAPI dependencies."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session as DBSession

from app.config import get_settings
from app.database.connection import get_db


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    """Minimal shared-secret auth for the admin dashboard APIs. Swap for
    real authenticated admin sessions before deploying for real -- this
    dependency is the single point that would change."""
    settings = get_settings()
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid admin credentials (X-Admin-Key header).",
        )


def get_current_user(
    authorization: str | None = Header(default=None), db: DBSession = Depends(get_db)
):
    """Resolves a self-serve customer's `Authorization: Bearer <session
    token>` header to their `User` row -- the one dependency every
    app/api/builder.py route uses, so "which user is this" is decided here
    once rather than re-derived per endpoint. Deliberately separate from
    `require_admin`: a customer session can never pass as platform-admin
    credentials and vice versa, they are different trust boundaries."""
    from app.models.user import User
    from app.models.user_session import UserSession
    from app.security.tokens import hash_token

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid session. Please log in again."
    )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise unauthorized
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise unauthorized

    session_row = db.query(UserSession).filter(UserSession.token_hash == hash_token(token)).first()
    if session_row is None or session_row.expires_at < datetime.utcnow():
        raise unauthorized

    user = db.query(User).filter(User.id == session_row.user_id).first()
    if user is None or not user.is_active:
        raise unauthorized
    return user


@dataclass
class Principal:
    """Who is calling an admin-screen endpoint. Two completely different
    trust boundaries can both reach these routes now:

    - The platform operator, via the single shared `X-Admin-Key` --
      `is_platform_admin=True`, `user_id=None`, sees and manages every
      agent on the platform (unchanged from before).
    - A self-serve customer, via their own `Authorization: Bearer <session
      token>` -- `is_platform_admin=False`, `user_id` set to their own
      `User.id`. Every endpoint that accepts a `Principal` is responsible
      for filtering its query (or checking ownership of a specific row)
      by `owner_user_id == principal.user_id` whenever
      `is_platform_admin` is False, the same 404-not-403 pattern already
      used throughout app/api/builder.py.

    The admin key always wins if both happen to be present/valid -- there
    is no scenario where that should matter in practice, but it keeps the
    precedence simple and explicit rather than implicit."""
    is_platform_admin: bool
    user_id: int | None


def get_admin_principal(
    x_admin_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    db: DBSession = Depends(get_db),
) -> Principal:
    settings = get_settings()
    if x_admin_key and x_admin_key == settings.ADMIN_SECRET_KEY:
        return Principal(is_platform_admin=True, user_id=None)

    # Not the platform operator -- fall back to a self-serve customer
    # session. Reuses get_current_user's exact validation (same hashed
    # lookup, same expiry check, same inactive-user check) so there is
    # only one place that logic lives; it raises its own 401 on failure.
    user = get_current_user(authorization=authorization, db=db)
    return Principal(is_platform_admin=False, user_id=user.id)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
