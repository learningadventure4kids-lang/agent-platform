"""`AIProviderFactory.create(config)` is the only place a `provider_type`
string gets turned into a concrete provider implementation. Every other
part of the codebase (agents, LangGraph, tools, RAG, the admin API) works
against the `AIProvider` interface only -- adding a new provider type
means adding one class + one line in `_IMPLEMENTATIONS` here, nothing
else.
"""
from __future__ import annotations

from dataclasses import replace

from app.ai.base import AIProvider
from app.ai.capabilities import ProviderCapabilities
from app.ai.errors import ProviderError, ProviderErrorCode
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.models.ai_provider import AIProviderConfig

# provider_type -> implementation class. OpenAI-compatible covers every
# provider that speaks the OpenAI chat-completions wire format, which is
# most of them -- see app/ai/providers/openai_compatible.py.
_IMPLEMENTATIONS: dict[str, type[AIProvider]] = {
    "ollama": OllamaProvider,
    "groq": OpenAICompatibleProvider,
    "openai": OpenAICompatibleProvider,
    "openrouter": OpenAICompatibleProvider,
    "azure_openai": OpenAICompatibleProvider,
    "custom_openai": OpenAICompatibleProvider,
}

# Registered but not yet implemented -- selectable in the admin UI's
# provider-type dropdown (per the brief) so the option exists, but
# creating/using one raises a clean, explicit error rather than silently
# misbehaving or crashing deep in LangChain. Implementing either is: write
# app/ai/providers/anthropic.py or google.py (same AIProvider interface),
# add it to _IMPLEMENTATIONS above -- no other code changes needed.
_NOT_YET_IMPLEMENTED = {"anthropic", "google"}


def _apply_capability_overrides(base: ProviderCapabilities, config: AIProviderConfig) -> ProviderCapabilities:
    overrides = {}
    for field in (
        "supports_tools", "supports_streaming", "supports_vision",
        "supports_structured_output", "supports_embeddings", "supports_reasoning",
    ):
        value = getattr(config, field)
        if value is not None:
            overrides[field] = value
    return replace(base, **overrides) if overrides else base


class AIProviderFactory:
    @staticmethod
    def create(config: AIProviderConfig) -> AIProvider:
        if not config.enabled:
            raise ProviderError(
                ProviderErrorCode.PROVIDER_DISABLED,
                f"Provider '{config.display_name}' is disabled.",
            )

        if config.provider_type in _NOT_YET_IMPLEMENTED:
            raise ProviderError(
                ProviderErrorCode.PROVIDER_CONFIGURATION_ERROR,
                f"Provider type '{config.provider_type}' is registered but not yet implemented.",
            )

        impl = _IMPLEMENTATIONS.get(config.provider_type)
        if impl is None:
            raise ProviderError(
                ProviderErrorCode.PROVIDER_CONFIGURATION_ERROR,
                f"Unknown provider type '{config.provider_type}'.",
            )

        provider = impl(config)
        provider.capabilities = _apply_capability_overrides(provider.capabilities, config)
        return provider


ALL_PROVIDER_TYPES = sorted(set(_IMPLEMENTATIONS) | _NOT_YET_IMPLEMENTED)
IMPLEMENTED_PROVIDER_TYPES = sorted(_IMPLEMENTATIONS)
