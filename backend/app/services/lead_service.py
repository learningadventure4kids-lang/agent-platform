"""Generic lead creation + scoring. Agent-specific fields (product
interest, birth details, budget, etc.) are passed through as `metadata`
rather than dedicated columns -- see app/models/lead.py."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.models.customer import Customer
from app.models.lead import Lead

BASE_FIELDS_WEIGHT = 40  # name + contact info
METADATA_FIELD_WEIGHT = 10  # each additional populated metadata field
MAX_SCORE = 100


def compute_lead_score(
    name: Optional[str], email: Optional[str], phone: Optional[str], metadata: dict
) -> int:
    score = 0
    if name:
        score += 15
    if email or phone:
        score += 25
    populated_extra = sum(1 for v in metadata.values() if v not in (None, "", []))
    score += min(populated_extra * METADATA_FIELD_WEIGHT, MAX_SCORE - score)
    return min(score, MAX_SCORE)


def create_lead(
    db: DBSession,
    agent_id: int,
    session_id: Optional[str],
    customer: Optional[Customer],
    name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    source: str,
    metadata: Optional[dict] = None,
) -> Lead:
    metadata = metadata or {}
    score = compute_lead_score(name, email, phone, metadata)
    lead = Lead(
        agent_id=agent_id,
        session_id=session_id,
        customer_id=customer.id if customer else None,
        name=name or (customer.name if customer else None),
        email=email or (customer.email if customer else None),
        phone=phone or (customer.phone if customer else None),
        source=source,
        status="qualified" if score >= 60 else "new",
        score=score,
        metadata_json=metadata,
    )
    db.add(lead)
    db.flush()
    return lead


def mark_contacted(db: DBSession, lead: Lead) -> Lead:
    lead.status = "contacted"
    lead.metadata_json = {**lead.metadata_json, "contacted_at": datetime.utcnow().isoformat()}
    db.flush()
    return lead


def mark_converted(db: DBSession, lead: Lead) -> Lead:
    lead.status = "converted"
    lead.metadata_json = {**lead.metadata_json, "converted_at": datetime.utcnow().isoformat()}
    db.flush()
    return lead
