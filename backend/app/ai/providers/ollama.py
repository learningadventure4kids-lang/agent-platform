from __future__ import annotations

import time
from typing import Optional

import httpx
from langchain_ollama import ChatOllama

from app.ai.base import AIProvider, ProviderOverrides, TestResult
from app.ai.capabilities import ProviderCapabilities
from app.ai.errors import ProviderErrorCode
from app.models.ai_provider import AIProviderConfig


class OllamaProvider(AIProvider):
    capabilities = ProviderCapabilities(
        supports_tools=True,
        supports_streaming=True,
        supports_vision=False,
        supports_structured_output=True,
        supports_reasoning=True,
    )

    def __init__(self, config: AIProviderConfig):
        self.config = config

    @property
    def provider_type(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self.config.model_name

    def get_chat_model(self, overrides: Optional[ProviderOverrides] = None):
        overrides = overrides or ProviderOverrides()
        return ChatOllama(
            model=overrides.model_name or self.config.model_name,
            base_url=self.config.base_url,
            temperature=overrides.temperature if overrides.temperature is not None else self.config.temperature,
        )

    def list_models(self) -> Optional[list[str]]:
        try:
            resp = httpx.get(f"{self.config.base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            return [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:
            return None

    def test_connection(self) -> TestResult:
        # Cheaper and more informative than a full generation: check the
        # server is reachable and the configured model is actually pulled,
        # matching what /api/health already does for the platform-wide check.
        started = time.monotonic()
        try:
            resp = httpx.get(f"{self.config.base_url}/api/tags", timeout=self.config.timeout or 10.0)
            resp.raise_for_status()
        except httpx.TimeoutException:
            return TestResult(
                success=False, provider=self.provider_type,
                error_code=ProviderErrorCode.PROVIDER_TIMEOUT,
                message="Ollama did not respond in time.",
            )
        except Exception:
            return TestResult(
                success=False, provider=self.provider_type,
                error_code=ProviderErrorCode.MODEL_UNAVAILABLE,
                message="Could not reach the Ollama server at the configured base URL.",
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        models = [m.get("name", "") for m in resp.json().get("models", [])]
        model_present = any(
            self.config.model_name == m or m.startswith(self.config.model_name.split(":")[0])
            for m in models
        )
        if not model_present:
            return TestResult(
                success=False, provider=self.provider_type, model=self.config.model_name,
                error_code=ProviderErrorCode.MODEL_NOT_FOUND,
                message=f"Model '{self.config.model_name}' is not pulled on this Ollama server.",
            )
        return TestResult(
            success=True, provider=self.provider_type, model=self.config.model_name, latency_ms=latency_ms
        )
