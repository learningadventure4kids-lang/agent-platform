"""Standardized errors for AI provider configuration/execution problems.
Every provider implementation and the factory raise `ProviderError` with
one of these codes rather than letting a raw SDK exception (which may
contain request/response details, headers, or partial credentials)
propagate to the API layer. `app/api/*` code catches `ProviderError` and
returns `{success, error_code, message}` -- never the underlying
exception's stack trace or `str(exc)` of the raw SDK error.
"""
from __future__ import annotations


class ProviderErrorCode:
    PROVIDER_DISABLED = "PROVIDER_DISABLED"
    PROVIDER_NOT_FOUND = "PROVIDER_NOT_FOUND"
    INVALID_API_KEY = "INVALID_API_KEY"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    PROVIDER_CONFIGURATION_ERROR = "PROVIDER_CONFIGURATION_ERROR"


class ProviderError(Exception):
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        self.message = message
        super().__init__(f"{error_code}: {message}")


def classify_error(exc: Exception) -> str:
    """Maps a raw provider/SDK exception to a standardized error code,
    purely by inspecting its message -- never touches request/response
    internals or credentials, so it's safe to call on any exception."""
    text = str(exc).lower()
    if "timeout" in text or "timed out" in text:
        return ProviderErrorCode.PROVIDER_TIMEOUT
    if "401" in text or "unauthorized" in text or "authentication" in text or "api key" in text:
        return ProviderErrorCode.INVALID_API_KEY
    if "404" in text or "not found" in text or "does not exist" in text:
        return ProviderErrorCode.MODEL_NOT_FOUND
    if "429" in text or "rate limit" in text:
        return ProviderErrorCode.RATE_LIMITED
    return ProviderErrorCode.MODEL_UNAVAILABLE


def safe_error_message(exc: Exception) -> str:
    """A message safe to show an admin: describes the failure category
    without leaking request/response internals or credentials."""
    code = classify_error(exc)
    return {
        ProviderErrorCode.PROVIDER_TIMEOUT: "The provider did not respond in time.",
        ProviderErrorCode.INVALID_API_KEY: "The provider rejected the API key.",
        ProviderErrorCode.MODEL_NOT_FOUND: "The configured model was not found.",
        ProviderErrorCode.RATE_LIMITED: "The provider is rate-limiting this request.",
    }.get(code, "The provider request failed.")
