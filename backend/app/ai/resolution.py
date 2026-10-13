"""Turns an `Agent` row into a ready-to-use LangChain chat model.

This is the one place that combines "which provider is this agent
configured for" with "build me something LangGraph can call `.invoke()`/
`.bind_tools()` on" -- `app/agents/factory.py::get_llm` is a thin wrapper
around `resolve_chat_model` below, kept as a separate module so the
resolution logic (provider lookup, default fallback, runtime
primary/fallback wrapping) is independently testable from the one-line
LangGraph integration point.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.ai.base import ProviderOverrides
from app.ai.errors import ProviderError, ProviderErrorCode, classify_error
from app.ai.factory import AIProviderFactory
from app.models.agent import Agent
from app.models.ai_provider import AIProviderConfig

logger = logging.getLogger("agent_platform.ai")

# Failure categories the fallback provider (if configured) may kick in
# for. Deliberately excludes INVALID_API_KEY and PROVIDER_CONFIGURATION_ERROR
# -- a bad credential or config is not a transient failure, and silently
# falling back would hide a misconfiguration from the admin rather than
# surfacing it (per the project brief).
_RETRYABLE_FOR_FALLBACK = {
    ProviderErrorCode.PROVIDER_TIMEOUT,
    ProviderErrorCode.RATE_LIMITED,
    ProviderErrorCode.MODEL_UNAVAILABLE,
    ProviderErrorCode.PROVIDER_DISABLED,
}


def get_default_provider(db: DBSession) -> Optional[AIProviderConfig]:
    return (
        db.query(AIProviderConfig)
        .filter(AIProviderConfig.is_default.is_(True), AIProviderConfig.enabled.is_(True))
        .first()
    )


def set_as_default_provider(db: DBSession, provider: AIProviderConfig) -> None:
    """Enforces the "at most one default provider" invariant. This is the
    one place that invariant is enforced -- both the admin API
    (app/api/admin_providers.py) and tests use this rather than setting
    `is_default = True` directly, so the invariant can never be
    accidentally bypassed by a new call site."""
    db.query(AIProviderConfig).filter(
        AIProviderConfig.is_default.is_(True), AIProviderConfig.id != provider.id
    ).update({"is_default": False})
    provider.is_default = True
    db.flush()


def set_default_provider(db: DBSession, provider: AIProviderConfig) -> None:
    """The single place that enforces 'at most one default provider at a
    time' -- clears is_default on every other row, then sets it on this
    one. Used by both the admin API (app/api/admin_providers.py) and
    seeding (app/seed.py) so the invariant holds regardless of call path,
    not just when going through one specific endpoint."""
    db.query(AIProviderConfig).filter(AIProviderConfig.id != provider.id).update({"is_default": False})
    provider.is_default = True
    db.flush()


def resolve_provider_config_for_agent(db: DBSession, agent: Agent) -> AIProviderConfig:
    """The agent's own provider if set (and enabled); otherwise the
    platform default. Raises PROVIDER_NOT_FOUND if neither exists, which
    should only happen on a fresh, never-seeded database."""
    config: Optional[AIProviderConfig] = None
    if agent.provider_id:
        config = db.query(AIProviderConfig).filter(AIProviderConfig.id == agent.provider_id).first()
        if config and not config.enabled:
            logger.warning(
                "agent_id=%s configured provider_id=%s is disabled, falling back to platform default",
                agent.id, agent.provider_id,
            )
            config = None

    if config is None:
        config = get_default_provider(db)

    if config is None:
        raise ProviderError(
            ProviderErrorCode.PROVIDER_NOT_FOUND,
            "No AI provider is configured for this agent, and no platform default provider exists.",
        )
    return config


def get_capabilities_for_agent(db: DBSession, agent: Agent):
    """Used by the graph to check an optional capability (tool calling)
    before relying on it -- see app/agents/graph.py::build_graph."""
    config = resolve_provider_config_for_agent(db, agent)
    provider = AIProviderFactory.create(config)
    return provider.capabilities


class _FallbackChatModel:
    """Duck-types the subset of the LangChain chat-model interface this
    platform's LangGraph actually uses (`bind_tools`, `invoke`). Not a real
    `BaseChatModel` subclass -- deliberately minimal so it stays simple
    and never needs to satisfy LangChain's pydantic model machinery."""

    def __init__(self, primary, fallback, agent_id: int, log_context: dict):
        self._primary = primary
        self._fallback = fallback
        self._agent_id = agent_id
        self._log_context = log_context

    def bind_tools(self, tools):
        bound_primary = self._primary.bind_tools(tools) if tools else self._primary
        bound_fallback = (
            (self._fallback.bind_tools(tools) if tools else self._fallback) if self._fallback else None
        )
        return _FallbackChatModel(bound_primary, bound_fallback, self._agent_id, self._log_context)

    def invoke(self, *args, **kwargs):
        try:
            return self._primary.invoke(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            if self._fallback is None:
                raise
            error_code = classify_error(exc)
            if error_code not in _RETRYABLE_FOR_FALLBACK:
                raise
            logger.warning(
                "provider failure, using fallback: agent_id=%s error_category=%s %s",
                self._agent_id, error_code, self._log_context,
            )
            return self._fallback.invoke(*args, **kwargs)


def resolve_chat_model(db: DBSession, agent: Agent):
    """Returns a chat model ready for `.bind_tools()`/`.invoke()`, already
    wrapped with the agent's fallback provider if one is configured."""
    primary_config = resolve_provider_config_for_agent(db, agent)
    primary_provider = AIProviderFactory.create(primary_config)
    overrides = ProviderOverrides(
        model_name=agent.model or None, temperature=agent.temperature, max_tokens=agent.max_tokens
    )
    primary_model = primary_provider.get_chat_model(overrides)

    if not agent.fallback_provider_id:
        return primary_model

    fallback_config = (
        db.query(AIProviderConfig).filter(AIProviderConfig.id == agent.fallback_provider_id).first()
    )
    if not fallback_config or not fallback_config.enabled:
        logger.warning("agent_id=%s fallback_provider_id is missing/disabled, ignoring", agent.id)
        return primary_model

    fallback_provider = AIProviderFactory.create(fallback_config)
    fallback_model = fallback_provider.get_chat_model()

    return _FallbackChatModel(
        primary_model,
        fallback_model,
        agent.id,
        {"provider_type": primary_config.provider_type, "model": primary_config.model_name},
    )
