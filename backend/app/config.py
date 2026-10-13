"""Central configuration for the multi-tenant agent platform. Everything is
overridable via environment variables / a .env file."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Aria Agent Platform")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # CORS for the *admin dashboard* only. The public chat API is embedded on
    # arbitrary third-party sites, so it is not gated by browser CORS -- it
    # is gated by the agent's allowed_domains list, checked server-side
    # (see app/security/domains.py). Never widen this list to "*" once
    # ADMIN_SECRET_KEY protects real data.
    CORS_ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv(
            "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if o.strip()
    ]

    # Postgres + pgvector is now the platform's database: the knowledge base
    # feature needs real vector similarity search, which SQLite can't do.
    # Still just a SQLAlchemy URL -- nothing in the app talks to psycopg
    # directly, so this remains the one place to change for a different host.
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/agent_platform"
    )

    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:8b")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", OLLAMA_MODEL)
    LLM_REQUEST_TIMEOUT: float = float(os.getenv("LLM_REQUEST_TIMEOUT", "60"))

    # --- Knowledge base / RAG ---
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "ollama")  # "ollama" | "deterministic"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "768"))

    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(20 * 1024 * 1024)))  # 20 MB
    ALLOWED_FILE_EXTENSIONS: list[str] = [
        e.strip().lower()
        for e in os.getenv("ALLOWED_FILE_EXTENSIONS", "pdf,docx,txt,csv,json,md,xlsx").split(",")
        if e.strip()
    ]

    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    TOP_K: int = int(os.getenv("TOP_K", "4"))

    WORKER_COUNT: int = int(os.getenv("WORKER_COUNT", "1"))
    WORKER_POLL_INTERVAL_SECONDS: float = float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "2"))

    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "changeme123")
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "dev-admin-secret-change-me")

    # HMAC key used when hashing public agent tokens for storage. Changing
    # this invalidates all existing tokens, so treat it like any other secret.
    TOKEN_HASH_SECRET: str = os.getenv("TOKEN_HASH_SECRET", "dev-token-secret-change-me")

    # Key used to encrypt AI provider API keys at rest, reversibly (see
    # app/security/encryption.py). Changing this makes existing encrypted
    # provider credentials undecryptable -- re-enter them after rotating.
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "dev-encryption-key-change-me")

    # Platform-level fallback used only to seed the initial default
    # provider on first startup (see app/seed.py). After that, all model
    # configuration lives in the ai_providers table, admin-editable.
    OLLAMA_DEFAULT_BASE_URL: str = os.getenv(
        "OLLAMA_DEFAULT_BASE_URL", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
    RATE_LIMIT_PER_MINUTE_PER_IP: int = int(os.getenv("RATE_LIMIT_PER_MINUTE_PER_IP", "60"))

    SEED_DEMO_DATA: bool = _bool(os.getenv("SEED_DEMO_DATA"), default=True)

    # --- Self-serve builder (app/api/user_auth.py, app/api/builder.py) ---
    # How long a signup/login session token stays valid before the user
    # has to log in again (see app/api/deps.py::get_current_user).
    USER_SESSION_TTL_HOURS: int = int(os.getenv("USER_SESSION_TTL_HOURS", "720"))  # 30 days

    # Used only to render the generated embed snippet text (never read by
    # any auth/security check) -- where the widget script is hosted and
    # what base URL it should call for /api/chat. Point these at your real
    # CDN/API domain in production; the localhost defaults are only
    # correct for local dev.
    PUBLIC_WIDGET_SCRIPT_URL: str = os.getenv("PUBLIC_WIDGET_SCRIPT_URL", "http://localhost:8000/static/aria-widget.js")
    PUBLIC_API_BASE_URL: str = os.getenv("PUBLIC_API_BASE_URL", "http://localhost:8000")


@lru_cache
def get_settings() -> Settings:
    return Settings()
