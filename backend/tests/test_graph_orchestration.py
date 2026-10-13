"""Integration tests for the LangGraph orchestration layer
(app/agents/graph.py): permission enforcement, the audit log, timeouts and
human handoff -- run against the *real* graph (compiled StateGraph, real
tool functions, real database), with only the chat model itself faked out.

A FakeChatModel here duck-types exactly what NativeToolCallPlanner needs
(`bind_tools()` -> itself, `.invoke()` -> the next scripted AIMessage), so
these tests exercise the actual node wiring -- agent_decision ->
validate_action -> permission_check -> execute_tool -> process_result ->
continue_decision -> ... -> respond -- not a mock of it.
"""
from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agents import graph as graph_module
from app.agents.graph import run_turn
from app.database.connection import db_session
from app.models.agent import Agent
from app.models.ai_provider import AIProviderConfig
from app.models.session import Session as SessionModel
from app.models.tool_execution_log import STATUS_DENIED, STATUS_SUCCESS, STATUS_TIMEOUT, ToolExecutionLog
from app.security.tokens import generate_token, hash_token


class FakeChatModel:
    """Scripted stand-in for a provider's bound chat model. Each call to
    `.invoke()` pops the next canned response, so a test scripts an entire
    multi-round conversation (tool call -> tool result -> final reply) up
    front."""

    def __init__(self, responses):
        self._responses = list(responses)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return self._responses.pop(0)


def _make_agent_and_session(db, key):
    # Each test gets its own explicit, enabled provider (rather than relying
    # on whatever happens to be the platform's ambient default) so these
    # tests are correct regardless of what order the suite runs in and
    # regardless of what other tests have done to the shared default-provider
    # row in this session's one Postgres database.
    provider = AIProviderConfig(
        provider_type="ollama", display_name=f"{key}-provider", enabled=True, is_default=False,
        base_url="http://localhost:11434", model_name="qwen3:8b", temperature=0.4,
    )
    db.add(provider)
    db.flush()
    agent = Agent(
        agent_key=key,
        tenant_id=key,
        public_token_hash=hash_token(generate_token()),
        name="Test Assistant",
        brand_name=key,
        system_prompt="You are a helpful assistant for testing.",
        welcome_message="hi",
        provider_id=provider.id,
    )
    db.add(agent)
    db.flush()
    session = SessionModel(agent_id=agent.id)
    db.add(session)
    db.flush()
    return agent, session


def _tool_call_message(name: str, args: dict, call_id: str = "call1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def test_confirmation_required_tool_is_denied_without_confirmed_flag(client, monkeypatch):
    with db_session() as db:
        agent, session = _make_agent_and_session(db, "confirm-denied")

        fake_llm = FakeChatModel([
            _tool_call_message("create_lead", {"confirmed": False, "email": "visitor@example.com"}),
            AIMessage(content="Okay, let me know when you're ready."),
        ])
        monkeypatch.setattr(graph_module, "get_llm", lambda db, agent: fake_llm)

        result = run_turn(
            db=db, agent=agent, session=session, customer=None,
            allowed_tool_keys=["create_lead"], history=[], user_message="sign me up",
        )

        assert result.ctx.leads_created == []
        assert "Okay, let me know" in result.assistant_text
        assert result.state["denied_actions"]
        assert result.state["denied_actions"][0]["reason"] == "confirmation_required"

        logs = db.query(ToolExecutionLog).filter(ToolExecutionLog.session_id == session.session_id).all()
        assert len(logs) == 1
        assert logs[0].status == STATUS_DENIED
        assert logs[0].error_category == "confirmation_required"
        # the raw email must never land in the audit log
        assert "visitor@example.com" not in str(logs[0].sanitized_arguments)
        assert logs[0].sanitized_arguments.get("email") is True


def test_confirmed_tool_call_executes_and_is_audited(client, monkeypatch):
    with db_session() as db:
        agent, session = _make_agent_and_session(db, "confirm-allowed")

        fake_llm = FakeChatModel([
            _tool_call_message(
                "create_lead",
                {"confirmed": True, "email": "visitor@example.com", "name": "Vera"},
            ),
            AIMessage(content="All set, someone will reach out."),
        ])
        monkeypatch.setattr(graph_module, "get_llm", lambda db, agent: fake_llm)

        result = run_turn(
            db=db, agent=agent, session=session, customer=None,
            allowed_tool_keys=["create_lead"], history=[], user_message="yes go ahead",
        )

        assert len(result.ctx.leads_created) == 1
        assert result.state["lead_created"] is True

        logs = db.query(ToolExecutionLog).filter(ToolExecutionLog.session_id == session.session_id).all()
        assert len(logs) == 1
        assert logs[0].status == STATUS_SUCCESS
        assert logs[0].sanitized_arguments.get("email") is True  # redacted, not the raw address


def test_tool_call_outside_agents_permissions_is_denied_as_tool_not_allowed(client, monkeypatch):
    """Even if a misbehaving/compromised provider response names a tool
    this agent was never granted, permission_check must deny it -- the
    model's tool_calls are a request, never a grant (see app/agents/action_planner.py)."""
    with db_session() as db:
        agent, session = _make_agent_and_session(db, "not-allowed")

        fake_llm = FakeChatModel([
            _tool_call_message("search_properties", {"query": "anything"}),
            AIMessage(content="I can't help with that here."),
        ])
        monkeypatch.setattr(graph_module, "get_llm", lambda db, agent: fake_llm)

        # Deliberately NOT granting search_properties.
        result = run_turn(
            db=db, agent=agent, session=session, customer=None,
            allowed_tool_keys=["create_lead"], history=[], user_message="find me a house",
        )

        assert result.state["denied_actions"][0]["reason"] == "tool_not_allowed"
        logs = db.query(ToolExecutionLog).filter(ToolExecutionLog.session_id == session.session_id).all()
        assert logs[0].status == STATUS_DENIED
        assert logs[0].error_category == "tool_not_allowed"


def test_tool_timeout_is_recorded_and_does_not_crash_the_turn(client, monkeypatch):
    import time

    from langchain_core.tools import StructuredTool

    def _slow_fn() -> str:
        time.sleep(0.2)
        return "too slow"

    slow_tool = StructuredTool.from_function(func=_slow_fn, name="get_known_info", description="slow")

    monkeypatch.setattr(graph_module, "build_tools_for_agent", lambda ctx, keys: [slow_tool])
    monkeypatch.setattr(
        graph_module, "get_tool_metadata",
        lambda key: {"requires_confirmation": False, "timeout_seconds": 0.01},
    )

    with db_session() as db:
        agent, session = _make_agent_and_session(db, "timeout-agent")

        fake_llm = FakeChatModel([
            _tool_call_message("get_known_info", {}),
            AIMessage(content="Sorry about the delay."),
        ])
        monkeypatch.setattr(graph_module, "get_llm", lambda db, agent: fake_llm)

        result = run_turn(
            db=db, agent=agent, session=session, customer=None,
            allowed_tool_keys=["get_known_info"], history=[], user_message="hi",
        )

        assert "Sorry about the delay" in result.assistant_text
        logs = db.query(ToolExecutionLog).filter(ToolExecutionLog.session_id == session.session_id).all()
        assert logs[0].status == STATUS_TIMEOUT
        assert logs[0].error_category == "tool_timeout"


def test_human_handoff_flag_propagates_without_exposing_internals(client, monkeypatch):
    with db_session() as db:
        agent, session = _make_agent_and_session(db, "handoff-agent")

        fake_llm = FakeChatModel([
            _tool_call_message("request_human_handoff", {"reason": "wants to speak to a person"}),
            AIMessage(content="I can connect you with a team member."),
        ])
        monkeypatch.setattr(graph_module, "get_llm", lambda db, agent: fake_llm)

        result = run_turn(
            db=db, agent=agent, session=session, customer=None,
            allowed_tool_keys=["request_human_handoff"], history=[], user_message="I want to talk to a human",
        )

        assert result.state["handoff_requested"] is True
        assert result.state["handoff_reason"] == "wants to speak to a person"
        assert result.ctx.handoff_requested is True
        # the visitor-facing text must stay generic -- no tool names, no internals
        assert "request_human_handoff" not in result.assistant_text
        assert "connect you with a team member" in result.assistant_text


def test_no_tool_call_turn_never_touches_audit_log(client, monkeypatch):
    with db_session() as db:
        agent, session = _make_agent_and_session(db, "no-tools-turn")

        fake_llm = FakeChatModel([AIMessage(content="Just chatting, no action needed.")])
        monkeypatch.setattr(graph_module, "get_llm", lambda db, agent: fake_llm)

        result = run_turn(
            db=db, agent=agent, session=session, customer=None,
            allowed_tool_keys=["create_lead"], history=[], user_message="hello",
        )

        assert result.assistant_text == "Just chatting, no action needed."
        logs = db.query(ToolExecutionLog).filter(ToolExecutionLog.session_id == session.session_id).all()
        assert logs == []
