"""The provider abstraction. `app/agents/factory.py::get_llm` is the only
caller of `AIProviderFactory.create(...)`, and everything downstream
(LangGraph, tools, RAG) only ever sees the plain LangChain `BaseChatModel`
returned by `get_chat_model()` -- no provider-specific type or code leaks
past this module. Adding a new provider means adding one new class here
and one line in `app/ai/factory.py`; nothing in `app/agents/graph.py` or
`app/tools/*` ever needs to change.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.ai.capabilities import ProviderCapabilities
from app.ai.errors import classify_error, safe_error_message


@dataclass
class ProviderOverrides:
    """Per-agent overrides layered on top of a provider's own defaults --
    e.g. two agents can share the "Groq" provider but use different models
    or temperatures."""

    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@dataclass
class TestResult:
    success: bool
    provider: str
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


class AIProvider(ABC):
    capabilities: ProviderCapabilities = ProviderCapabilities()

    @abstractmethod
    def get_chat_model(self, overrides: Optional[ProviderOverrides] = None) -> BaseChatModel:
        """Returns a ready-to-use LangChain chat model. Never returns
        anything provider-specific to the caller beyond the standard
        BaseChatModel interface (.invoke, .bind_tools, .stream, ...)."""

    def list_models(self) -> Optional[list[str]]:
        """Returns available model names, or None if this provider doesn't
        support discovery (manual model entry is always allowed either
        way)."""
        return None

    def test_connection(self) -> TestResult:
        """Sends one minimal request and reports success/failure + latency.
        Default implementation works for any provider exposing a
        LangChain-compatible chat model; providers needing a cheaper/more
        specific check (e.g. Ollama's /api/tags) can override this."""
        model = self.get_chat_model()
        started = time.monotonic()
        try:
            model.invoke([HumanMessage(content="ping")])
        except Exception as exc:  # noqa: BLE001
            return TestResult(
                success=False,
                provider=self.provider_type,
                error_code=classify_error(exc),
                message=safe_error_message(exc),
            )
        latency_ms = int((time.monotonic() - started) * 1000)
        return TestResult(
            success=True, provider=self.provider_type, model=self.model_name, latency_ms=latency_ms
        )

    @property
    @abstractmethod
    def provider_type(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


def require_capability(provider: AIProvider, capability: str) -> None:
    if not getattr(provider.capabilities, capability, False):
        from app.ai.errors import ProviderError, ProviderErrorCode

        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY,
            f"The selected provider/model does not support '{capability}'.",
        )
