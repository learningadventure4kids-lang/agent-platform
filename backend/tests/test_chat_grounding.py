import logging

from app.api.chat import _looks_like_ungrounded_success_claim
from app.database.connection import db_session
from app.models.session import Session as SessionModel
from app.security.tokens import generate_token, hash_token
from app.tools.common import ToolContext, build_common_tools


class _FakeCtx:
    def __init__(self, leads_created):
        self.leads_created = leads_created


def test_flags_success_language_with_no_lead_created():
    ctx = _FakeCtx(leads_created=[])
    text = "Great, I've saved your details and someone will reach out soon!"
    assert _looks_like_ungrounded_success_claim(text, ctx) is True


def test_does_not_flag_when_a_lead_was_actually_created():
    ctx = _FakeCtx(leads_created=[object()])
    text = "Great, I've saved your details and someone will reach out soon!"
    assert _looks_like_ungrounded_success_claim(text, ctx) is False


def test_does_not_flag_ordinary_conversation():
    ctx = _FakeCtx(leads_created=[])
    text = "Sure, what's your date of birth?"
    assert _looks_like_ungrounded_success_claim(text, ctx) is False


def test_does_not_flag_when_asking_for_confirmation():
    ctx = _FakeCtx(leads_created=[])
    text = "Here's what I have so far -- would you like me to submit this request?"
    # "submit" alone (without "submitted your") shouldn't trigger.
    assert _looks_like_ungrounded_success_claim(text, ctx) is False


def _make_agent(db, key: str):
    from app.models.agent import Agent

    agent = Agent(
        agent_key=key, tenant_id=key, public_token_hash=hash_token(generate_token()),
        name="Test", brand_name=key, system_prompt="x", welcome_message="hi",
    )
    db.add(agent)
    db.flush()
    return agent


def test_create_lead_failure_is_logged_with_reason(caplog):
    with db_session() as db:
        agent = _make_agent(db, "ground-1")
        session = SessionModel(agent_id=agent.id)
        db.add(session)
        db.flush()
        ctx = ToolContext(db=db, agent=agent, session=session, customer=None)
        tools = build_common_tools(ctx, source="test-widget")

        with caplog.at_level(logging.WARNING, logger="agent_platform.tools"):
            result = tools["create_lead"].invoke({"confirmed": False})

        assert "confirmation was not affirmative" in result
        assert ctx.tool_results[-1]["success"] is False
        assert any("confirmed=false" in rec.message for rec in caplog.records)


def test_create_lead_success_is_logged(caplog):
    with db_session() as db:
        agent = _make_agent(db, "ground-2")
        session = SessionModel(agent_id=agent.id)
        db.add(session)
        db.flush()
        ctx = ToolContext(db=db, agent=agent, session=session, customer=None)
        tools = build_common_tools(ctx, source="test-widget")

        with caplog.at_level(logging.INFO, logger="agent_platform.tools"):
            result = tools["create_lead"].invoke(
                {"confirmed": True, "name": "Jo", "email": "jo@example.com"}
            )

        assert "created successfully" in result
        assert ctx.leads_created
        assert ctx.tool_results[-1]["success"] is True
        assert any("lead #" in rec.message for rec in caplog.records)


def test_missing_contact_info_failure_is_logged(caplog):
    with db_session() as db:
        agent = _make_agent(db, "ground-3")
        session = SessionModel(agent_id=agent.id)
        db.add(session)
        db.flush()
        ctx = ToolContext(db=db, agent=agent, session=session, customer=None)
        tools = build_common_tools(ctx, source="test-widget")

        result = tools["create_lead"].invoke({"confirmed": True, "name": "Jo"})

        assert "no email or phone" in result
        assert ctx.tool_results[-1]["success"] is False
        assert "no email or phone" in ctx.tool_results[-1]["result"]
