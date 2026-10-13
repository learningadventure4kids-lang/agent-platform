from __future__ import annotations

import os
import tempfile

# IMPORTANT: these must be set before any `app.*` module is imported
# anywhere (including by other test modules), since app.config caches
# settings and app.database.connection builds its engine at import time.
#
# Tests run against a REAL local Postgres + pgvector database (not SQLite)
# so retrieval/tenant-isolation tests exercise the actual vector search
# code path, not a mock of it. Point TEST_DATABASE_URL at your own Postgres
# instance if the default local one isn't available.
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/agent_platform_test"
)
os.environ["SEED_DEMO_DATA"] = "true"
os.environ["ADMIN_SECRET_KEY"] = "test-admin-secret"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password"
os.environ["TOKEN_HASH_SECRET"] = "test-token-secret"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_PER_MINUTE_PER_IP"] = "1000"

# Deterministic, dependency-free embeddings so the whole suite (including
# ingestion + retrieval + isolation tests) runs without a live Ollama
# instance. A small dimension keeps pgvector index/queries fast in CI.
os.environ["EMBEDDING_PROVIDER"] = "deterministic"
os.environ["VECTOR_DIMENSION"] = "32"
os.environ["CHUNK_SIZE"] = "300"
os.environ["CHUNK_OVERLAP"] = "50"

_UPLOAD_DIR = tempfile.mkdtemp(prefix="agent_platform_uploads_")
os.environ["UPLOAD_DIR"] = _UPLOAD_DIR

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database.connection import engine, init_db  # noqa: E402

# Start every test run from a clean, schema-only database.
with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

init_db()


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_headers():
    return {"X-Admin-Key": "test-admin-secret"}


@pytest.fixture(scope="session")
def agent_tokens(client, admin_headers):
    """Resolve the seeded sample agents' public tokens by rotating each
    once (rotation returns the new plaintext token) -- this avoids relying
    on parsing the .seeded_tokens.txt side file in tests."""
    resp = client.get("/api/admin/agents", headers=admin_headers)
    agents = {a["agent_key"]: a["id"] for a in resp.json()}
    tokens = {}
    for key, agent_id in agents.items():
        r = client.post(f"/api/admin/agents/{agent_id}/rotate-token", headers=admin_headers)
        tokens[key] = {"token": r.json()["public_token"], "id": agent_id}
    return tokens
