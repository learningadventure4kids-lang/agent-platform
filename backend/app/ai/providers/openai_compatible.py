"""One implementation for every provider that speaks the OpenAI
chat-completions wire format: Groq, OpenAI itself, OpenRouter,
Azure OpenAI's OpenAI-compatible endpoint mode, and any other
"custom OpenAI-compatible" endpoint an admin points at. This is exactly
the reusable abstraction the project brief asks for -- adding Groq or a
future compatible provider is a `base_url` + API key in the admin panel,
never a new Python class.
"""
from __future__ import annotations

from typing import Optional

import httpx
from langchain_openai import ChatOpenAI

from app.ai.base import AIProvider, ProviderOverrides
from app.ai.capabilities import ProviderCapabilities
from app.models.ai_provider import AIProviderConfig
from app.security.encryption import decrypt_secret

# Known base URLs, used only to pre-fill the admin form / for display --
# never hard-coded into request logic. A "custom" provider_type supplies
# its own base_url directly.
KNOWN_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


class OpenAICompatibleProvider(AIProvider):
    capabilities = ProviderCapabilities(
        supports_tools=True,
        supports_streaming=True,
        supports_vision=False,
        supports_structured_output=True,
    )

    def __init__(self, config: AIProviderConfig):
        self.config = config

    @property
    def provider_type(self) -> str:
        return self.config.provider_type

    @property
    def model_name(self) -> str:
        return self.config.model_name

    def _api_key(self) -> Optional[str]:
        if not self.config.encrypted_api_key:
            return None
        return decrypt_secret(self.config.encrypted_api_key)

    def get_chat_model(self, overrides: Optional[ProviderOverrides] = None):
        overrides = overrides or ProviderOverrides()
        kwargs = dict(
            model=overrides.model_name or self.config.model_name,
            base_url=self.config.base_url or KNOWN_BASE_URLS.get(self.config.provider_type),
            # Some self-hosted OpenAI-compatible servers don't check the key
            # at all, but the langchain-openai/openai SDK still requires a
            # non-empty string to construct the client -- a placeholder is
            # harmless for those, and cloud providers that DO require a key
            # will simply reject it at request time with a clean
            # INVALID_API_KEY-classified error.
            api_key=self._api_key() or "not-required",
            temperature=overrides.temperature if overrides.temperature is not None else self.config.temperature,
            timeout=self.config.timeout or 60,
        )
        max_tokens = overrides.max_tokens or self.config.max_tokens
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        return ChatOpenAI(**kwargs)

    def list_models(self) -> Optional[list[str]]:
        base_url = self.config.base_url or KNOWN_BASE_URLS.get(self.config.provider_type)
        api_key = self._api_key()
        if not base_url or not api_key:
            return None
        try:
            resp = httpx.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
            return [m.get("id", "") for m in data if m.get("id")]
        except Exception:
            # Not every OpenAI-compatible provider implements model listing
            # (or the API key may not have permission to) -- manual model
            # entry always remains available, so this just returns None.
            return None
