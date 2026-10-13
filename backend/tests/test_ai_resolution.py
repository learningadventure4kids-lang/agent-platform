import pytest

from app.ai.errors import ProviderError, ProviderErrorCode
from app.ai.resolution import (
    _FallbackChatModel,
    get_capabilities_for_agent,
    get_default_provider,
    resolve_provider_config_for_agent,
)
from app.database.connection import db_session
from app.models.agent import Agent
from app.models.ai_provider import AIProviderConfig
from app.security.tokens import generate_token, hash_token


def _make_agent(db, key: str, **overrides):
    agent = Agent(
        agent_key=key,
        tenant_id=key,
        public_token_hash=hash_token(generate_token()),
        name="Test",
        brand_name=key,
        system_prompt="x",
        welcome_message="hi",
        **overrides,
    )
    db.add(agent)
    db.flush()
    return agent


def _make_provider(db, **overrides):
    defaults = dict(
        provider_type="ollama", display_name="Test Provider", enabled=True, is_default=False,
        base_url="http://localhost:11434", model_name="qwen3:8b", temperature=0.4,
    )
    want_default = overrides.pop("is_default", defaults["is_default"])
    defaults.update(overrides)
    provider = AIProviderConfig(**defaults)
    db.add(provider)
    db.flush()
    if want_default:
        # Enforces the "only one default" invariant the same way the admin
        # API does (see app/ai/resolution.py::set_as_default_provider),
        # rather than setting is_default=True directly -- this test suite
        # shares one Postgres database across the whole session, so
        # without this, earlier tests' default providers would make
        # get_default_provider()'s result order-dependent/nondeterministic.
        from app.ai.resolution import set_as_default_provider

        set_as_default_provider(db, provider)
    return provider


def test_agent_with_no_provider_resolves_to_platform_default():
    with db_session() as db:
        default = _make_provider(db, display_name="Platform Default", is_default=True)
        agent = _make_agent(db, "resolve-1")
        resolved = resolve_provider_config_for_agent(db, agent)
        assert resolved.id == default.id


def test_agent_with_explicit_provider_uses_it_not_default():
    with db_session() as db:
        _make_provider(db, display_name="Default", is_default=True)
        groq = _make_provider(db, display_name="Groq", provider_type="groq", is_default=False)
        agent = _make_agent(db, "resolve-2", provider_id=groq.id)
        resolved = resolve_provider_config_for_agent(db, agent)
        assert resolved.id == groq.id
        assert resolved.provider_type == "groq"


def test_agent_with_disabled_explicit_provider_falls_back_to_default():
    with db_session() as db:
        default = _make_provider(db, display_name="Default", is_default=True)
        disabled = _make_provider(db, display_name="Disabled Groq", provider_type="groq", enabled=False)
        agent = _make_agent(db, "resolve-3", provider_id=disabled.id)
        resolved = resolve_provider_config_for_agent(db, agent)
        assert resolved.id == default.id


def test_no_provider_at_all_raises_provider_not_found():
    with db_session() as db:
        # This suite shares one database across the whole session (which
        # already has the seeded default Ollama provider by the time this
        # test runs), so "no provider at all" is simulated by temporarily
        # disabling every existing provider rather than assuming a truly
        # empty table -- restored at the end so later tests are unaffected.
        existing = db.query(AIProviderConfig).all()
        previous_enabled = {p.id: p.enabled for p in existing}
        for p in existing:
            p.enabled = False
        db.flush()

        try:
            agent = _make_agent(db, "resolve-4")
            with pytest.raises(ProviderError) as exc_info:
                resolve_provider_config_for_agent(db, agent)
            assert exc_info.value.error_code == ProviderErrorCode.PROVIDER_NOT_FOUND
        finally:
            for p in existing:
                p.enabled = previous_enabled[p.id]
            db.flush()


def test_two_agents_use_different_providers_simultaneously():
    with db_session() as db:
        ollama = _make_provider(db, display_name="Ollama", provider_type="ollama", is_default=True)
        groq = _make_provider(db, display_name="Groq", provider_type="groq", is_default=False)
        agent_a = _make_agent(db, "multi-a")  # default -> ollama
        agent_b = _make_agent(db, "multi-b", provider_id=groq.id)  # explicit -> groq

        resolved_a = resolve_provider_config_for_agent(db, agent_a)
        resolved_b = resolve_provider_config_for_agent(db, agent_b)

        assert resolved_a.provider_type == "ollama"
        assert resolved_b.provider_type == "groq"
        assert resolved_a.id != resolved_b.id


def test_get_default_provider_ignores_disabled_default():
    """Regression guard: `_make_provider(..., is_default=True)` goes through
    `set_as_default_provider`, which clears `is_default` on every *other*
    row -- including whatever the platform's real seeded default was. Since
    this suite shares one Postgres database across the whole session, this
    test must restore the previous default afterward (in `finally`) or every
    test that runs later and relies on an ambient default provider existing
    (e.g. anything that builds an agent's LangGraph without an explicit
    provider_id) would start failing purely due to test ordering -- exactly
    the kind of order-dependent flakiness this suite has hit before."""
    with db_session() as db:
        previous_default = (
            db.query(AIProviderConfig).filter(AIProviderConfig.is_default.is_(True)).first()
        )
        try:
            _make_provider(db, display_name="Disabled Default", is_default=True, enabled=False)
            assert get_default_provider(db) is None
        finally:
            if previous_default is not None:
                db.query(AIProviderConfig).filter(AIProviderConfig.id != previous_default.id).update(
                    {"is_default": False}
                )
                previous_default.is_default = True
                db.flush()


def test_get_capabilities_for_agent_reflects_provider_type():
    with db_session() as db:
        groq = _make_provider(db, display_name="Groq", provider_type="groq", supports_tools=False)
        agent = _make_agent(db, "caps-1", provider_id=groq.id)
        caps = get_capabilities_for_agent(db, agent)
        assert caps.supports_tools is False


# --- _FallbackChatModel: unit tests against fake primary/fallback models
# (no real network / provider construction needed here) ---

class _FakeModel:
    def __init__(self, fail_with: Exception | None = None, response="ok"):
        self.fail_with = fail_with
        self.response = response
        self.invoked = False

    def invoke(self, *args, **kwargs):
        self.invoked = True
        if self.fail_with:
            raise self.fail_with
        return self.response

    def bind_tools(self, tools):
        return self


def test_fallback_triggers_on_retryable_error():
    primary = _FakeModel(fail_with=Exception("Request timed out"))
    fallback = _FakeModel(response="fallback response")
    wrapper = _FallbackChatModel(primary, fallback, agent_id=1, log_context={})

    result = wrapper.invoke("hi")
    assert result == "fallback response"
    assert primary.invoked and fallback.invoked


def test_fallback_does_not_trigger_on_invalid_api_key():
    """Per the project brief: never silently fall back on bad credentials
    -- that hides a real misconfiguration from the admin."""
    primary = _FakeModel(fail_with=Exception("401 Unauthorized: invalid api key"))
    fallback = _FakeModel(response="should not be used")
    wrapper = _FallbackChatModel(primary, fallback, agent_id=1, log_context={})

    with pytest.raises(Exception, match="401"):
        wrapper.invoke("hi")
    assert not fallback.invoked


def test_no_fallback_configured_raises_original_error():
    primary = _FakeModel(fail_with=Exception("Request timed out"))
    wrapper = _FallbackChatModel(primary, None, agent_id=1, log_context={})
    with pytest.raises(Exception, match="timed out"):
        wrapper.invoke("hi")


def test_successful_primary_never_touches_fallback():
    primary = _FakeModel(response="primary response")
    fallback = _FakeModel(response="fallback response")
    wrapper = _FallbackChatModel(primary, fallback, agent_id=1, log_context={})

    result = wrapper.invoke("hi")
    assert result == "primary response"
    assert not fallback.invoked


def test_bind_tools_preserves_fallback_wrapping():
    primary = _FakeModel(fail_with=Exception("rate limit exceeded, 429"))
    fallback = _FakeModel(response="fallback after bind_tools")
    wrapper = _FallbackChatModel(primary, fallback, agent_id=1, log_context={})

    bound = wrapper.bind_tools(["fake-tool"])
    assert isinstance(bound, _FallbackChatModel)
    result = bound.invoke("hi")
    assert result == "fallback after bind_tools"
