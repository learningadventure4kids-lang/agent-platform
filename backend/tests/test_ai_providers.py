import pytest

from app.ai.errors import ProviderErrorCode, classify_error
from app.ai.factory import ALL_PROVIDER_TYPES, AIProviderFactory
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.models.ai_provider import AIProviderConfig
from app.security.encryption import decrypt_secret, encrypt_secret


def _config(**overrides):
    defaults = dict(
        provider_type="ollama", display_name="Test", enabled=True, is_default=False,
        base_url="http://localhost:11434", model_name="qwen3:8b", temperature=0.4,
    )
    defaults.update(overrides)
    return AIProviderConfig(**defaults)


def test_factory_creates_ollama_provider():
    provider = AIProviderFactory.create(_config(provider_type="ollama"))
    assert isinstance(provider, OllamaProvider)
    assert provider.provider_type == "ollama"


def test_factory_creates_groq_via_openai_compatible():
    provider = AIProviderFactory.create(_config(provider_type="groq", model_name="llama-3.1-8b-instant"))
    assert isinstance(provider, OpenAICompatibleProvider)


def test_factory_creates_custom_openai_compatible():
    provider = AIProviderFactory.create(
        _config(provider_type="custom_openai", base_url="https://my-llm.example.com/v1")
    )
    assert isinstance(provider, OpenAICompatibleProvider)


def test_factory_rejects_disabled_provider():
    from app.ai.errors import ProviderError

    with pytest.raises(ProviderError) as exc_info:
        AIProviderFactory.create(_config(enabled=False))
    assert exc_info.value.error_code == ProviderErrorCode.PROVIDER_DISABLED


def test_factory_rejects_unimplemented_provider_type():
    from app.ai.errors import ProviderError

    with pytest.raises(ProviderError) as exc_info:
        AIProviderFactory.create(_config(provider_type="anthropic"))
    assert exc_info.value.error_code == ProviderErrorCode.PROVIDER_CONFIGURATION_ERROR


def test_factory_rejects_unknown_provider_type():
    from app.ai.errors import ProviderError

    with pytest.raises(ProviderError) as exc_info:
        AIProviderFactory.create(_config(provider_type="totally-made-up"))
    assert exc_info.value.error_code == ProviderErrorCode.PROVIDER_CONFIGURATION_ERROR


def test_anthropic_and_google_are_registered_but_not_implemented():
    assert "anthropic" in ALL_PROVIDER_TYPES
    assert "google" in ALL_PROVIDER_TYPES


def test_capability_override_from_db_row():
    provider = AIProviderFactory.create(_config(provider_type="groq", supports_tools=False))
    assert provider.capabilities.supports_tools is False


def test_capability_default_unaffected_when_not_overridden():
    provider = AIProviderFactory.create(_config(provider_type="ollama"))
    assert provider.capabilities.supports_tools is True  # Ollama's coded default


def test_groq_chat_model_uses_configured_base_url_and_key():
    config = _config(
        provider_type="groq",
        base_url="https://api.groq.com/openai/v1",
        model_name="llama-3.1-8b-instant",
        encrypted_api_key=encrypt_secret("sk-test-key"),
    )
    provider = AIProviderFactory.create(config)
    model = provider.get_chat_model()
    assert model.openai_api_base == "https://api.groq.com/openai/v1"
    assert model.model_name == "llama-3.1-8b-instant"


def test_custom_provider_without_api_key_does_not_crash_construction():
    """Self-hosted OpenAI-compatible servers may not require a key at all
    -- constructing the chat model must not fail just because none is
    configured (see app/ai/providers/openai_compatible.py)."""
    config = _config(provider_type="custom_openai", base_url="http://localhost:8080/v1")
    provider = AIProviderFactory.create(config)
    model = provider.get_chat_model()
    assert model is not None


# --- Error classification ---

def test_classify_timeout_error():
    assert classify_error(Exception("Request timed out after 30s")) == ProviderErrorCode.PROVIDER_TIMEOUT


def test_classify_auth_error():
    assert classify_error(Exception("401 Unauthorized: invalid api key")) == ProviderErrorCode.INVALID_API_KEY


def test_classify_model_not_found():
    assert classify_error(Exception("404 model does not exist")) == ProviderErrorCode.MODEL_NOT_FOUND


def test_classify_rate_limited():
    assert classify_error(Exception("429 rate limit exceeded")) == ProviderErrorCode.RATE_LIMITED


def test_classify_unknown_defaults_to_model_unavailable():
    assert classify_error(Exception("connection refused")) == ProviderErrorCode.MODEL_UNAVAILABLE


# --- Encryption ---

def test_encrypt_decrypt_roundtrip():
    secret = "sk-super-secret-key"
    encrypted = encrypt_secret(secret)
    assert encrypted != secret
    assert decrypt_secret(encrypted) == secret


def test_encrypted_value_does_not_contain_plaintext():
    secret = "sk-groq-abcdef123456"
    encrypted = encrypt_secret(secret)
    assert secret not in encrypted
