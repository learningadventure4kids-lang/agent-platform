from app.database.connection import db_session
from app.models.customer import Customer
from app.models.session import Session as SessionModel
from app.tools.common import ToolContext
from app.tools.registry import TOOL_REGISTRY, build_tools_for_agent


def _fake_ctx():
    with db_session() as db:
        session = SessionModel(agent_id=1)
        db.add(session)
        db.flush()
        customer = Customer(name="Test")
        db.add(customer)
        db.flush()

        class FakeAgent:
            id = 1
            agent_key = "fake-agent"
            tenant_id = "fake-tenant"

        return ToolContext(db=db, agent=FakeAgent(), session=session, customer=customer)


def test_agent_only_gets_its_own_allowed_tools():
    ctx = _fake_ctx()
    kaur_tools = build_tools_for_agent(ctx, ["search_jewellery", "get_product_details", "create_jewellery_lead"])
    tool_names = {t.name for t in kaur_tools}
    assert tool_names == {"search_jewellery", "get_product_details", "create_jewellery_lead"}


def test_agent_a_does_not_receive_agent_b_tools():
    ctx = _fake_ctx()
    # Kaur Jewellery's permission list does NOT include astrology tools.
    kaur_allowed = ["search_jewellery", "get_product_details", "create_jewellery_lead", "create_lead"]
    kaur_tools = build_tools_for_agent(ctx, kaur_allowed)
    tool_names = {t.name for t in kaur_tools}

    assert "calculate_birth_chart" not in tool_names
    assert "create_astrology_consultation" not in tool_names
    assert "search_properties" not in tool_names


def test_unknown_tool_key_is_silently_ignored():
    ctx = _fake_ctx()
    tools = build_tools_for_agent(ctx, ["search_jewellery", "not_a_real_tool"])
    assert {t.name for t in tools} == {"search_jewellery"}


def test_empty_permission_list_yields_no_tools():
    ctx = _fake_ctx()
    assert build_tools_for_agent(ctx, []) == []


def test_every_registry_entry_is_independently_buildable():
    """Every tool_key advertised in TOOL_REGISTRY (shown in the admin
    dashboard) must actually resolve to a real tool when granted alone --
    otherwise an admin could "enable" a tool that silently does nothing."""
    for tool_key in TOOL_REGISTRY:
        ctx = _fake_ctx()
        tools = build_tools_for_agent(ctx, [tool_key])
        assert len(tools) == 1, f"{tool_key} did not resolve to exactly one tool"
        assert tools[0].name == tool_key
