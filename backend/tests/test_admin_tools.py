def test_list_tools_requires_auth(client):
    assert client.get("/api/admin/tools").status_code == 401


def test_list_tools_includes_registry_entries(client, admin_headers):
    resp = client.get("/api/admin/tools", headers=admin_headers)
    keys = {t["tool_key"] for t in resp.json()}
    assert "search_jewellery" in keys
    assert "calculate_birth_chart" in keys
    assert "search_properties" in keys


def test_get_agent_tools_shows_granted_flags(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["astrology"]["id"]
    resp = client.get(f"/api/admin/agents/{agent_id}/tools", headers=admin_headers)
    by_key = {t["tool_key"]: t["granted"] for t in resp.json()}
    assert by_key["calculate_birth_chart"] is True
    assert by_key["search_jewellery"] is False


def test_update_agent_tools_replaces_permissions(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["real-estate"]["id"]
    resp = client.put(
        f"/api/admin/agents/{agent_id}/tools",
        json={"tool_keys": ["create_lead"]},
        headers=admin_headers,
    )
    by_key = {t["tool_key"]: t["granted"] for t in resp.json()}
    assert by_key["create_lead"] is True
    assert by_key["search_properties"] is False  # revoked

    # restore for other tests relying on the seeded permission set
    client.put(
        f"/api/admin/agents/{agent_id}/tools",
        json={"tool_keys": ["search_properties", "get_property_details", "create_lead"]},
        headers=admin_headers,
    )
