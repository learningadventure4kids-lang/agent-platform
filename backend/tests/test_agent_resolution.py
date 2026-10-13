from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.agents.resolver import resolve_agent
from app.database.connection import db_session
from app.models.agent import Agent
from app.security.tokens import generate_token, hash_token


def _make_agent(**overrides):
    token = generate_token()
    defaults = dict(
        agent_key=f"test-agent-{token[-6:]}",
        tenant_id=f"test-tenant-{token[-6:]}",
        public_token_hash=hash_token(token),
        name="Test",
        brand_name="Test Brand",
        system_prompt="You are a test agent.",
        welcome_message="Hi!",
        enabled=True,
        allowed_domains=[],
    )
    defaults.update(overrides)
    with db_session() as db:
        agent = Agent(**defaults)
        db.add(agent)
        db.flush()
        agent_id = agent.id
    return token, agent_id


def _request_with_origin(origin=None):
    req = MagicMock()
    req.headers = {"origin": origin} if origin else {}
    return req


def test_resolve_agent_with_valid_token():
    token, _ = _make_agent()
    with db_session() as db:
        agent = resolve_agent(db, token)
        assert agent.public_token_hash == hash_token(token)


def test_resolve_agent_with_invalid_token_raises_401():
    with db_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            resolve_agent(db, "pub_not-a-real-token")
        assert exc_info.value.status_code == 401


def test_resolve_agent_with_missing_token_raises_401():
    with db_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            resolve_agent(db, "")
        assert exc_info.value.status_code == 401


def test_resolve_agent_disabled_raises_403():
    token, _ = _make_agent(enabled=False)
    with db_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            resolve_agent(db, token)
        assert exc_info.value.status_code == 403


def test_resolve_agent_domain_restricted_blocks_other_origins():
    token, _ = _make_agent(allowed_domains=["kaurjewellery.com"])
    with db_session() as db:
        with pytest.raises(HTTPException) as exc_info:
            resolve_agent(db, token, _request_with_origin("https://evil.example.com"))
        assert exc_info.value.status_code == 403


def test_resolve_agent_domain_restricted_allows_matching_origin():
    token, _ = _make_agent(allowed_domains=["kaurjewellery.com"])
    with db_session() as db:
        agent = resolve_agent(db, token, _request_with_origin("https://kaurjewellery.com"))
        assert agent is not None
