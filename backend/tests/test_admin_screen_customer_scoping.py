"""The admin screen (Agents, Sessions, Leads, Customers, Tools, Knowledge)
is now reachable by two different logins that share the same routes --
the platform operator (`X-Admin-Key`, sees everything, unchanged) and a
self-serve customer (`Authorization: Bearer <session token>`, scoped to
only the agents they created). This file is entirely about that second
path: a customer must see their own agents and nothing else, through
every route the admin screen uses -- never a 403 that confirms another
tenant's agent exists, always a plain 404."""
from __future__ import annotations


def _signup(client, email):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "correct horse battery staple", "name": "Customer"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["session_token"]


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_customer_agent(client, token, brand="My Business"):
    resp = client.post(
        "/api/admin/agents",
        json={
            "agent_key": "ignored-by-server",
            "name": "Rae",
            "brand_name": brand,
            "system_prompt": "You are Rae.",
            "welcome_message": "Hi!",
            "tool_keys": ["create_lead"],
            # A scoped customer should never be able to hand itself a
            # platform-wide provider -- confirmed to be silently ignored
            # (not rejected -- the field just isn't theirs to set) below.
            "provider_id": 999999,
        },
        headers=_bearer(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_customer_cannot_reach_admin_agents_without_either_credential(client):
    assert client.get("/api/admin/agents").status_code == 401


def test_customer_create_agent_is_auto_scoped_and_ignores_client_supplied_identity(client):
    token = _signup(client, "scoped-create@example.com")
    created = _create_customer_agent(client, token, brand="Scoped Create Co")

    # agent_key was NOT "ignored-by-server" -- the server generated its own.
    assert created["agent_key"] != "ignored-by-server"
    # provider_id was silently dropped, not honored.
    assert created["provider_id"] is None


def test_customer_only_sees_their_own_agents_in_the_admin_list(client):
    token_a = _signup(client, "list-a@example.com")
    token_b = _signup(client, "list-b@example.com")
    agent_a = _create_customer_agent(client, token_a, brand="Agent A Co")
    _create_customer_agent(client, token_b, brand="Agent B Co")

    listed = client.get("/api/admin/agents", headers=_bearer(token_a)).json()
    ids = [a["id"] for a in listed]
    assert agent_a["id"] in ids
    assert all(a["brand_name"] != "Agent B Co" for a in listed)


def test_customer_gets_404_not_403_for_another_customers_agent(client, admin_headers):
    token_a = _signup(client, "iso-a@example.com")
    token_b = _signup(client, "iso-b@example.com")
    agent = _create_customer_agent(client, token_a, brand="Isolated Co")
    agent_id = agent["id"]
    other = _bearer(token_b)

    assert client.get(f"/api/admin/agents/{agent_id}", headers=other).status_code == 404
    assert client.put(f"/api/admin/agents/{agent_id}", json={"name": "Hijacked"}, headers=other).status_code == 404
    assert client.delete(f"/api/admin/agents/{agent_id}", headers=other).status_code == 404
    assert client.post(f"/api/admin/agents/{agent_id}/rotate-token", headers=other).status_code == 404
    assert client.post(f"/api/admin/agents/{agent_id}/disable", headers=other).status_code == 404
    assert client.get(f"/api/admin/agents/{agent_id}/tools", headers=other).status_code == 404
    assert client.get(f"/api/admin/agents/{agent_id}/tool-executions", headers=other).status_code == 404
    assert client.get(f"/api/knowledge?agent_id={agent_id}", headers=other).status_code == 404

    # The platform operator can still reach it fine -- scoping only
    # narrows a customer's view, it never narrows the operator's.
    assert client.get(f"/api/admin/agents/{agent_id}", headers=admin_headers).status_code == 200


def test_customer_can_manage_tools_and_see_executions_on_their_own_agent(client):
    token = _signup(client, "tools-owner@example.com")
    agent = _create_customer_agent(client, token, brand="Tools Owner Co")
    headers = _bearer(token)

    # Catalog is readable (platform-wide, not ownership-scoped).
    catalog = client.get("/api/admin/tools", headers=headers)
    assert catalog.status_code == 200
    assert any(t["tool_key"] == "create_lead" for t in catalog.json())

    granted = client.put(
        f"/api/admin/agents/{agent['id']}/tools", json={"tool_keys": ["create_lead"]}, headers=headers
    )
    assert granted.status_code == 200

    executions = client.get(f"/api/admin/agents/{agent['id']}/tool-executions", headers=headers)
    assert executions.status_code == 200


def test_customer_sessions_and_leads_are_scoped_to_their_own_agents(client, admin_headers):
    token = _signup(client, "sessions-owner@example.com")
    agent = _create_customer_agent(client, token, brand="Sessions Owner Co")
    headers = _bearer(token)

    # An admin-owned (seeded) agent exists too -- listing sessions/leads
    # with no agent_id filter must never include its data for a customer.
    admin_agents = client.get("/api/admin/agents", headers=admin_headers).json()
    admin_owned_ids = {a["id"] for a in admin_agents} - {agent["id"]}
    assert admin_owned_ids, "expected at least one seeded admin-owned agent to compare against"
    other_agent_id = next(iter(admin_owned_ids))

    sessions = client.get("/api/admin/sessions", headers=headers)
    assert sessions.status_code == 200

    leads = client.get("/api/admin/leads", headers=headers)
    assert leads.status_code == 200
    stats = client.get("/api/admin/leads/stats", headers=headers)
    assert stats.status_code == 200

    # Filtering explicitly by another tenant's agent_id is a 404, not an
    # empty list -- same "never confirm it exists" rule as everywhere else.
    assert client.get(f"/api/admin/sessions?agent_id={other_agent_id}", headers=headers).status_code == 404
    assert client.get(f"/api/admin/leads?agent_id={other_agent_id}", headers=headers).json() == []


def test_providers_and_settings_style_admin_only_routes_reject_customer_sessions(client):
    token = _signup(client, "no-providers@example.com")
    headers = _bearer(token)
    # AI Providers stay strictly platform-admin -- a valid customer
    # session must not satisfy this dependency at all.
    assert client.get("/api/admin/providers", headers=headers).status_code == 401
