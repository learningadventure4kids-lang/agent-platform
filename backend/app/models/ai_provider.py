"""Admin-configurable AI provider records. One row per configured
provider (an admin might have both "Ollama" and "Groq" rows, or even two
Groq rows with different models/keys). `encrypted_api_key` is the ONLY
place an API key is ever persisted -- always encrypted (see
app/security/encryption.py), never returned by any API response (see
AIProviderOut in app/schemas.py, which deliberately has no field for it).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class AIProviderConfig(Base):
    __tablename__ = "ai_providers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # "ollama" | "groq" | "openai" | "openrouter" | "azure_openai" | "custom_openai"
    # | "anthropic" | "google" -- the factory (app/ai/factory.py) maps this
    # to an implementation class. Unimplemented values raise a clean
    # PROVIDER_CONFIGURATION_ERROR rather than crashing, so they can be
    # added to this list ahead of having a working implementation.
    provider_type: Mapped[str] = mapped_column(String(40), index=True)
    display_name: Mapped[str] = mapped_column(String(120))

    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    base_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    encrypted_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_name: Mapped[str] = mapped_column(String(120))
    temperature: Mapped[float] = mapped_column(Float, default=0.4)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timeout: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Capability overrides: NULL means "use this provider type's coded
    # default" (see app/ai/capabilities.py); set explicitly when an admin
    # knows a specific model differs from the provider's usual capabilities
    # (e.g. a Groq-hosted model that doesn't support tool calling).
    supports_tools: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supports_streaming: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supports_vision: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supports_structured_output: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supports_embeddings: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supports_reasoning: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Provider-specific extras that don't warrant their own column yet
    # (e.g. an Azure deployment name or API version).
    configuration_json: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
