def test_admin_agents_require_auth(client):
    resp = client.get("/api/admin/agents")
    assert resp.status_code == 401


def test_create_agent_returns_token_once(client, admin_headers):
    payload = {
        "agent_key": "dental-clinic",
        "name": "Dana",
        "brand_name": "Bright Smile Dental",
        "system_prompt": "You are Dana, a friendly dental clinic assistant.",
        "welcome_message": "Hi! How can I help with your dental needs today?",
        "suggestions": ["Book an appointment", "Services"],
        "lead_fields": ["name", "email", "phone"],
        "tool_keys": ["create_lead"],
    }
    resp = client.post("/api/admin/agents", json=payload, headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["public_token"].startswith("pub_")
    assert body["tool_count"] == 1

    # The plaintext token is never returned again from GET.
    get_resp = client.get(f"/api/admin/agents/{body['id']}", headers=admin_headers)
    assert "public_token" not in get_resp.json()


def test_duplicate_agent_key_rejected(client, admin_headers):
    payload = {
        "agent_key": "kaur-jewellery",  # already seeded
        "name": "Duplicate",
        "brand_name": "Duplicate Co",
        "system_prompt": "x",
        "welcome_message": "x",
        "tool_keys": [],
    }
    resp = client.post("/api/admin/agents", json=payload, headers=admin_headers)
    assert resp.status_code == 409


def test_update_agent(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["real-estate"]["id"]
    resp = client.put(
        f"/api/admin/agents/{agent_id}",
        json={"welcome_message": "Updated welcome!"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["welcome_message"] == "Updated welcome!"


def test_rotate_token_invalidates_old_token(client, admin_headers):
    create = client.post(
        "/api/admin/agents",
        json={
            "agent_key": "rotate-test",
            "name": "R",
            "brand_name": "R Co",
            "system_prompt": "x",
            "welcome_message": "x",
            "tool_keys": [],
        },
        headers=admin_headers,
    ).json()
    old_token = create["public_token"]
    agent_id = create["id"]

    old_works = client.post("/api/session", json={"agent_token": old_token})
    assert old_works.status_code == 200

    rotate = client.post(f"/api/admin/agents/{agent_id}/rotate-token", headers=admin_headers)
    new_token = rotate.json()["public_token"]
    assert new_token != old_token

    old_now_fails = client.post("/api/session", json={"agent_token": old_token})
    assert old_now_fails.status_code == 401

    new_works = client.post("/api/session", json={"agent_token": new_token})
    assert new_works.status_code == 200


def test_disable_and_enable_agent(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["astrology"]["id"]
    token = agent_tokens["astrology"]["token"]

    client.post(f"/api/admin/agents/{agent_id}/disable", headers=admin_headers)
    resp = client.post("/api/session", json={"agent_token": token})
    assert resp.status_code == 403

    client.post(f"/api/admin/agents/{agent_id}/enable", headers=admin_headers)
    resp2 = client.post("/api/session", json={"agent_token": token})
    assert resp2.status_code == 200


def test_delete_agent(client, admin_headers):
    create = client.post(
        "/api/admin/agents",
        json={
            "agent_key": "delete-me",
            "name": "D",
            "brand_name": "D Co",
            "system_prompt": "x",
            "welcome_message": "x",
            "tool_keys": [],
        },
        headers=admin_headers,
    ).json()
    resp = client.delete(f"/api/admin/agents/{create['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert client.get(f"/api/admin/agents/{create['id']}", headers=admin_headers).status_code == 404
