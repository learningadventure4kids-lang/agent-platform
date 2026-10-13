"""Admin-only AI provider management. Every response schema
(`AIProviderOut`) exposes `api_key_configured: bool` only -- there is no
code path in this file that ever serializes `encrypted_api_key` or a
decrypted key back to the client. See app/schemas.py for the enforced
shape.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.ai.errors import ProviderError
from app.ai.factory import ALL_PROVIDER_TYPES, AIProviderFactory
from app.ai.resolution import set_as_default_provider
from app.api.deps import require_admin
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.ai_provider import AIProviderConfig
from app.schemas import AIProviderCreate, AIProviderOut, AIProviderUpdate, ProviderTestResultOut
from app.security.encryption import encrypt_secret

logger = logging.getLogger("agent_platform.ai_providers")

router = APIRouter(
    prefix="/api/admin/providers", tags=["admin-providers"], dependencies=[Depends(require_admin)]
)


def _to_out(db: DBSession, p: AIProviderConfig) -> AIProviderOut:
    agent_count = db.query(func.count(Agent.id)).filter(Agent.provider_id == p.id).scalar() or 0
    return AIProviderOut(
        id=p.id,
        provider_type=p.provider_type,
        display_name=p.display_name,
        enabled=p.enabled,
        is_default=p.is_default,
        base_url=p.base_url,
        api_key_configured=bool(p.encrypted_api_key),
        model_name=p.model_name,
        temperature=p.temperature,
        max_tokens=p.max_tokens,
        timeout=p.timeout,
        supports_tools=p.supports_tools,
        supports_streaming=p.supports_streaming,
        supports_vision=p.supports_vision,
        supports_structured_output=p.supports_structured_output,
        supports_embeddings=p.supports_embeddings,
        supports_reasoning=p.supports_reasoning,
        configuration_json=p.configuration_json,
        created_at=p.created_at,
        updated_at=p.updated_at,
        agent_count=agent_count,
    )


def _clear_other_defaults(db: DBSession, exclude_id: int | None = None) -> None:
    # Retained as a thin wrapper for the endpoints below that need to
    # clear defaults without necessarily setting a new one via
    # set_as_default_provider (e.g. create/update where is_default may or
    # may not be set in the same request).
    query = db.query(AIProviderConfig).filter(AIProviderConfig.is_default.is_(True))
    if exclude_id is not None:
        query = query.filter(AIProviderConfig.id != exclude_id)
    query.update({"is_default": False})


@router.get("", response_model=list[AIProviderOut])
def list_providers(db: DBSession = Depends(get_db)):
    providers = db.query(AIProviderConfig).order_by(AIProviderConfig.created_at.asc()).all()
    return [_to_out(db, p) for p in providers]


@router.get("/types")
def list_provider_types():
    """Provider types selectable in the admin form, including ones
    registered but not yet implemented (so the dropdown can show them as
    'coming soon' -- see app/ai/factory.py::_NOT_YET_IMPLEMENTED)."""
    from app.ai.factory import IMPLEMENTED_PROVIDER_TYPES

    return {
        "implemented": IMPLEMENTED_PROVIDER_TYPES,
        "all": ALL_PROVIDER_TYPES,
    }


@router.get("/{provider_id}", response_model=AIProviderOut)
def get_provider(provider_id: int, db: DBSession = Depends(get_db)):
    p = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Provider not found")
    return _to_out(db, p)


@router.post("", response_model=AIProviderOut)
def create_provider(payload: AIProviderCreate, db: DBSession = Depends(get_db)):
    data = payload.model_dump(exclude={"api_key"})
    provider = AIProviderConfig(**data)
    if payload.api_key:
        provider.encrypted_api_key = encrypt_secret(payload.api_key)

    db.add(provider)
    db.flush()
    if provider.is_default:
        _clear_other_defaults(db, exclude_id=provider.id)
    db.commit()
    db.refresh(provider)
    logger.info("provider created id=%s provider_type=%s", provider.id, provider.provider_type)
    return _to_out(db, provider)


@router.put("/{provider_id}", response_model=AIProviderOut)
def update_provider(provider_id: int, payload: AIProviderUpdate, db: DBSession = Depends(get_db)):
    provider = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    updates = payload.model_dump(exclude_unset=True, exclude={"api_key"})
    for field, value in updates.items():
        setattr(provider, field, value)

    if payload.api_key is not None:
        provider.encrypted_api_key = encrypt_secret(payload.api_key) if payload.api_key else None

    db.flush()
    if provider.is_default:
        _clear_other_defaults(db, exclude_id=provider.id)
    db.commit()
    db.refresh(provider)
    logger.info("provider updated id=%s", provider.id)
    return _to_out(db, provider)


@router.delete("/{provider_id}")
def delete_provider(provider_id: int, db: DBSession = Depends(get_db)):
    provider = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    in_use = db.query(func.count(Agent.id)).filter(
        (Agent.provider_id == provider_id) | (Agent.fallback_provider_id == provider_id)
    ).scalar() or 0
    if in_use:
        raise HTTPException(
            status_code=409,
            detail=f"{in_use} agent(s) are using this provider (as primary or fallback). Reassign them first.",
        )

    db.delete(provider)
    db.commit()
    logger.info("provider deleted id=%s", provider_id)
    return {"deleted": True, "provider_id": provider_id}


@router.post("/{provider_id}/set-default", response_model=AIProviderOut)
def set_default_provider(provider_id: int, db: DBSession = Depends(get_db)):
    provider = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    if not provider.enabled:
        raise HTTPException(status_code=400, detail="Cannot set a disabled provider as default.")

    set_as_default_provider(db, provider)
    db.commit()
    db.refresh(provider)
    return _to_out(db, provider)


@router.post("/{provider_id}/test", response_model=ProviderTestResultOut)
def test_provider(provider_id: int, db: DBSession = Depends(get_db)):
    provider_config = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not provider_config:
        raise HTTPException(status_code=404, detail="Provider not found")

    try:
        provider = AIProviderFactory.create(provider_config)
    except ProviderError as exc:
        logger.info(
            "provider test failed at construction id=%s error_code=%s", provider_id, exc.error_code
        )
        return ProviderTestResultOut(
            success=False, provider=provider_config.provider_type,
            error_code=exc.error_code, message=exc.message,
        )

    result = provider.test_connection()
    logger.info(
        "provider test id=%s provider_type=%s success=%s latency_ms=%s",
        provider_id, provider_config.provider_type, result.success, result.latency_ms,
    )
    return ProviderTestResultOut(
        success=result.success, provider=result.provider, model=result.model,
        latency_ms=result.latency_ms, error_code=result.error_code, message=result.message,
    )


@router.get("/{provider_id}/models")
def discover_models(provider_id: int, db: DBSession = Depends(get_db)):
    provider_config = db.query(AIProviderConfig).filter(AIProviderConfig.id == provider_id).first()
    if not provider_config:
        raise HTTPException(status_code=404, detail="Provider not found")

    try:
        provider = AIProviderFactory.create(provider_config)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=exc.message) from exc

    models = provider.list_models()
    if models is None:
        return {"supported": False, "models": []}
    return {"supported": True, "models": models}
