"""A self-serve platform customer -- distinct from the single shared
ADMIN_USERNAME/ADMIN_PASSWORD operator login (app/api/admin_auth.py). A
User owns zero or more Agents (Agent.owner_user_id) and can only ever see
or modify their own (enforced in app/api/builder.py, never by convention
alone -- every query there filters on owner_user_id)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.billing.plans import PLAN_FREE
from app.database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(200))

    name: Mapped[str] = mapped_column(String(120))
    company_name: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # "free" | "plus" -- see app/billing/plans.py for what each tier
    # allows. No payment processor yet; only a platform operator can move
    # a customer off the free tier today (PATCH /api/admin/users/{id}/plan).
    plan: Mapped[str] = mapped_column(String(20), default=PLAN_FREE)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
