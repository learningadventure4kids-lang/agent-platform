"""The self-serve builder: signup/login (app/api/user_auth.py) and the
persona -> create agent -> embed script flow (app/api/builder.py), plus
the cross-user isolation property that makes this safe to expose publicly
-- one customer must never see or modify another's agent."""
from __future__ import annotations

from app.database.connection import db_session
from app.services import customer_service, lead_service, session_service


def _signup(client, email="founder@example.com", password="correct horse battery staple"):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "name": "Founder", "company_name": "Acme Co"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_signup_then_me_returns_the_account(client):
    body = _signup(client, email="signup-me@example.com")
    assert body["user"]["email"] == "signup-me@example.com"
    assert body["session_token"]

    resp = client.get("/api/auth/me", headers=_auth_headers(body["session_token"]))
    assert resp.status_code == 200
    assert resp.json()["email"] == "signup-me@example.com"


def test_signup_rejects_duplicate_email(client):
    _signup(client, email="dupe@example.com")
    resp = client.post(
        "/api/auth/signup",
        json={"email": "dupe@example.com", "password": "another password", "name": "Someone"},
    )
    assert resp.status_code == 409


def test_login_requires_correct_password(client):
    _signup(client, email="login-test@example.com", password="the-real-password")
    bad = client.post("/api/auth/login", json={"email": "login-test@example.com", "password": "wrong"})
    assert bad.status_code == 401

    good = client.post(
        "/api/auth/login", json={"email": "login-test@example.com", "password": "the-real-password"}
    )
    assert good.status_code == 200
    assert good.json()["session_token"]


def test_builder_endpoints_require_a_session(client):
    resp = client.get("/api/builder/agents")
    assert resp.status_code == 401


def test_personas_are_public_but_agents_require_auth(client):
    # The persona catalog is deliberately public (a visitor should be able
    # to browse personas on the landing page before signing up) -- but
    # every actual agent route is still gated, confirmed by the test above
    # and the cross-user isolation tests below.
    resp = client.get("/api/builder/personas")
    assert resp.status_code == 200
    keys = {p["key"] for p in resp.json()}
    assert "real_estate" in keys and "custom" in keys


def test_create_agent_from_persona_returns_a_working_embed_snippet(client):
    auth = _signup(client, email="builder-create@example.com")
    headers = _auth_headers(auth["session_token"])

    resp = client.post(
        "/api/builder/agents",
        json={
            "persona_key": "real_estate",
            "name": "Remi",
            "brand_name": "Acme Realty",
            "accent_color": "#7c5cff",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["public_token"].startswith("pub_")
    assert "AriaWidget.mountFloating" in body["install_snippet"]
    assert body["public_token"] in body["install_snippet"]

    listed = client.get("/api/builder/agents", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["brand_name"] == "Acme Realty"
    assert listed[0]["persona_key"] == "real_estate"


def test_embed_snippet_omits_apiurl_when_widget_and_api_share_an_origin(client, monkeypatch):
    """The default config (widget script and API both on localhost:8000)
    is the common case this exists for: the customer shouldn't have to
    know or paste the API's URL at all. The widget (widget/src/index.tsx)
    infers it at runtime from its own <script src="..."> tag's origin, so
    the generated snippet should leave `apiUrl` out entirely here.

    `Settings` fields are evaluated once from the environment at import
    time (plain class attributes, not a pydantic BaseSettings re-read per
    instantiation), so a plain `monkeypatch.setenv` after import has no
    effect -- patch the already-constructed, cached instance's attributes
    directly instead, which is what the handler actually reads."""
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "PUBLIC_WIDGET_SCRIPT_URL", "http://localhost:8000/static/aria-widget.js")
    monkeypatch.setattr(settings, "PUBLIC_API_BASE_URL", "http://localhost:8000")

    auth = _signup(client, email="same-origin-snippet@example.com")
    resp = client.post(
        "/api/builder/agents",
        json={"persona_key": "custom", "name": "A", "brand_name": "Same Origin Co"},
        headers=_auth_headers(auth["session_token"]),
    )
    assert resp.status_code == 201, resp.text
    snippet = resp.json()["install_snippet"]
    assert "apiUrl" not in snippet
    assert 'src="http://localhost:8000/static/aria-widget.js"' in snippet
    assert "AriaWidget.mountFloating" in snippet


def test_embed_snippet_includes_apiurl_when_widget_is_served_from_a_different_origin(client, monkeypatch):
    """When the widget script is hosted elsewhere (e.g. a CDN) from the
    API, auto-detection from the script tag's own origin would infer the
    CDN's URL, not the API's -- so `apiUrl` must be included explicitly
    here, or the widget would silently talk to the wrong place."""
    from app.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "PUBLIC_WIDGET_SCRIPT_URL", "https://cdn.example.com/aria-widget.js")
    monkeypatch.setattr(settings, "PUBLIC_API_BASE_URL", "https://api.example.com")

    auth = _signup(client, email="cross-origin-snippet@example.com")
    resp = client.post(
        "/api/builder/agents",
        json={"persona_key": "custom", "name": "A", "brand_name": "Cross Origin Co"},
        headers=_auth_headers(auth["session_token"]),
    )
    assert resp.status_code == 201, resp.text
    snippet = resp.json()["install_snippet"]
    assert 'apiUrl: "https://api.example.com"' in snippet
    assert 'src="https://cdn.example.com/aria-widget.js"' in snippet


def test_rotated_token_also_gets_an_apiurl_free_snippet_by_default(client):
    """Rotation goes through the same `_build_embed_snippet` helper as
    creation (app/api/builder.py) -- confirm a rotated snippet is just as
    apiUrl-free as a freshly created one, not a stale code path."""
    auth = _signup(client, email="rotate-no-apiurl@example.com")
    headers = _auth_headers(auth["session_token"])
    created = client.post(
        "/api/builder/agents",
        json={"persona_key": "custom", "name": "R", "brand_name": "Rotate No ApiUrl Co"},
        headers=headers,
    ).json()

    rotated = client.post(f"/api/builder/agents/{created['agent_id']}/rotate-token", headers=headers)
    assert rotated.status_code == 200
    assert "apiUrl" not in rotated.json()["install_snippet"]
    assert rotated.json()["public_token"] in rotated.json()["install_snippet"]


def test_create_agent_rejects_unknown_persona(client):
    auth = _signup(client, email="builder-bad-persona@example.com")
    resp = client.post(
        "/api/builder/agents",
        json={"persona_key": "not-a-real-persona", "name": "X", "brand_name": "Y"},
        headers=_auth_headers(auth["session_token"]),
    )
    assert resp.status_code == 400


def test_created_agent_actually_gets_its_persona_tools(client):
    """The whole point of a persona is that the agent it creates is
    immediately usable -- confirm the tool grants (app/agents/registry.py)
    actually landed, not just that the HTTP call succeeded."""
    from app.agents.registry import get_allowed_tool_keys
    from app.database.connection import db_session

    auth = _signup(client, email="builder-tools@example.com")
    resp = client.post(
        "/api/builder/agents",
        json={"persona_key": "jewellery_retail", "name": "Gigi", "brand_name": "Gem Co"},
        headers=_auth_headers(auth["session_token"]),
    )
    agent_id = resp.json()["agent_id"]

    with db_session() as db:
        granted = set(get_allowed_tool_keys(db, agent_id))
    assert "search_jewellery" in granted
    assert "create_jewellery_lead" in granted
    assert "create_lead" in granted  # common tools are included too


def test_one_user_cannot_see_or_modify_another_users_agent(client):
    owner = _signup(client, email="owner@example.com")
    other = _signup(client, email="other@example.com")

    created = client.post(
        "/api/builder/agents",
        json={"persona_key": "custom", "name": "Mine", "brand_name": "Only Mine Inc"},
        headers=_auth_headers(owner["session_token"]),
    )
    agent_id = created.json()["agent_id"]

    # The owner can see it...
    assert client.get(f"/api/builder/agents/{agent_id}", headers=_auth_headers(owner["session_token"])).status_code == 200
    # ...but a different logged-in user gets a 404, not a 403 (never confirms existence).
    other_headers = _auth_headers(other["session_token"])
    assert client.get(f"/api/builder/agents/{agent_id}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/api/builder/agents/{agent_id}", json={"name": "Hijacked"}, headers=other_headers
    ).status_code == 404
    assert client.post(f"/api/builder/agents/{agent_id}/rotate-token", headers=other_headers).status_code == 404
    # And it never shows up in the other user's own agent list.
    other_list = client.get("/api/builder/agents", headers=other_headers).json()
    assert all(a["id"] != agent_id for a in other_list)


def test_rotate_token_issues_a_new_working_token(client):
    auth = _signup(client, email="rotate-test@example.com")
    headers = _auth_headers(auth["session_token"])
    created = client.post(
        "/api/builder/agents",
        json={"persona_key": "custom", "name": "R", "brand_name": "Rotate Co"},
        headers=headers,
    ).json()

    rotated = client.post(f"/api/builder/agents/{created['agent_id']}/rotate-token", headers=headers)
    assert rotated.status_code == 200
    assert rotated.json()["public_token"] != created["public_token"]

    # The new token actually works against the real public chat resolver.
    from app.agents.resolver import resolve_agent

    class _FakeRequest:
        headers: dict = {}
        client = None

    from app.database.connection import db_session

    with db_session() as db:
        resolved = resolve_agent(db, rotated.json()["public_token"], _FakeRequest())
        assert resolved.id == created["agent_id"]


def test_logout_invalidates_the_session_token(client):
    auth = _signup(client, email="logout-test@example.com")
    headers = _auth_headers(auth["session_token"])
    assert client.get("/api/auth/me", headers=headers).status_code == 200

    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_preview_chat_lets_owner_try_their_own_agent_without_the_public_token(client):
    """The dashboard's "see how it looks" preview authenticates by the
    customer's own session + ownership, not the plaintext public token
    (which is only ever shown once) -- but it should still run the real
    pipeline and return the agent's actual welcome/brand info."""
    auth = _signup(client, email="preview-test@example.com")
    headers = _auth_headers(auth["session_token"])
    created = client.post(
        "/api/builder/agents",
        json={"persona_key": "real_estate", "name": "Remi", "brand_name": "Preview Realty"},
        headers=headers,
    ).json()
    agent_id = created["agent_id"]

    resp = client.post(
        f"/api/builder/agents/{agent_id}/preview-chat",
        json={"message": "hi there"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["agent"]["brand"] == "Preview Realty"
    assert body["agent"]["name"] == "Remi"
    assert body["session_id"]

    # A second message in the same preview session reuses it (continuity).
    resp2 = client.post(
        f"/api/builder/agents/{agent_id}/preview-chat",
        json={"message": "tell me more", "session_id": body["session_id"]},
        headers=headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["session_id"] == body["session_id"]


def test_preview_chat_is_owner_scoped_like_every_other_builder_route(client):
    owner = _signup(client, email="preview-owner@example.com")
    other = _signup(client, email="preview-other@example.com")
    created = client.post(
        "/api/builder/agents",
        json={"persona_key": "custom", "name": "Mine", "brand_name": "Only Mine Preview Inc"},
        headers=_auth_headers(owner["session_token"]),
    ).json()

    resp = client.post(
        f"/api/builder/agents/{created['agent_id']}/preview-chat",
        json={"message": "hi"},
        headers=_auth_headers(other["session_token"]),
    )
    assert resp.status_code == 404

    resp = client.post(
        f"/api/builder/agents/{created['agent_id']}/preview-chat",
        json={"message": "hi"},
    )
    assert resp.status_code == 401


# --- Scoped "admin screen" for self-serve customers: same functionality
# as app/api/admin_*.py / app/api/leads.py, but every query is additionally
# filtered down to the caller's own agents (never the platform-admin
# X-Admin-Key path) -- see app/api/builder.py for the shared owner-scoping
# helpers these all build on. ---

def _create_agent(client, headers, brand_name="Owned Co", persona_key="custom"):
    resp = client.post(
        "/api/builder/agents",
        json={"persona_key": persona_key, "name": "A", "brand_name": brand_name},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_tool_catalog_is_visible_to_any_logged_in_customer(client):
    auth = _signup(client, email="tools-catalog@example.com")
    resp = client.get("/api/builder/tools", headers=_auth_headers(auth["session_token"]))
    assert resp.status_code == 200
    assert any(t["tool_key"] == "create_lead" for t in resp.json())

    assert client.get("/api/builder/tools").status_code == 401


def test_agent_tool_grants_are_owner_scoped_and_actually_take_effect(client):
    from app.agents.registry import get_allowed_tool_keys

    owner = _signup(client, email="tool-grants-owner@example.com")
    other = _signup(client, email="tool-grants-other@example.com")
    owner_headers = _auth_headers(owner["session_token"])
    created = _create_agent(client, owner_headers, brand_name="Tool Grants Co")
    agent_id = created["agent_id"]

    # The other user can't even see the grant list.
    assert client.get(
        f"/api/builder/agents/{agent_id}/tools", headers=_auth_headers(other["session_token"])
    ).status_code == 404

    resp = client.get(f"/api/builder/agents/{agent_id}/tools", headers=owner_headers)
    assert resp.status_code == 200
    assert any(t["tool_key"] == "create_lead" and t["granted"] for t in resp.json())

    # Revoking create_lead and granting a different tool actually changes
    # what the orchestration layer will allow -- not just the HTTP response.
    update = client.put(
        f"/api/builder/agents/{agent_id}/tools",
        json={"tool_keys": ["get_known_info"]},
        headers=owner_headers,
    )
    assert update.status_code == 200
    with db_session() as db:
        granted = set(get_allowed_tool_keys(db, agent_id))
    assert granted == {"get_known_info"}

    # And the other user still can't do it.
    assert client.put(
        f"/api/builder/agents/{agent_id}/tools",
        json={"tool_keys": ["get_known_info"]},
        headers=_auth_headers(other["session_token"]),
    ).status_code == 404


def test_tool_execution_log_is_owner_scoped(client):
    owner = _signup(client, email="tool-log-owner@example.com")
    other = _signup(client, email="tool-log-other@example.com")
    owner_headers = _auth_headers(owner["session_token"])
    created = _create_agent(client, owner_headers, brand_name="Tool Log Co")
    agent_id = created["agent_id"]

    assert client.get(f"/api/builder/agents/{agent_id}/tool-executions", headers=owner_headers).status_code == 200
    assert client.get(
        f"/api/builder/agents/{agent_id}/tool-executions", headers=_auth_headers(other["session_token"])
    ).status_code == 404


def test_delete_agent_is_owner_scoped_and_actually_removes_it(client):
    owner = _signup(client, email="delete-owner@example.com")
    other = _signup(client, email="delete-other@example.com")
    owner_headers = _auth_headers(owner["session_token"])
    created = _create_agent(client, owner_headers, brand_name="Delete Me Co")
    agent_id = created["agent_id"]

    assert client.delete(
        f"/api/builder/agents/{agent_id}", headers=_auth_headers(other["session_token"])
    ).status_code == 404

    resp = client.delete(f"/api/builder/agents/{agent_id}", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    assert client.get(f"/api/builder/agents/{agent_id}", headers=owner_headers).status_code == 404


def test_sessions_endpoint_only_shows_my_own_agents_sessions(client):
    alice = _signup(client, email="sessions-alice@example.com")
    bob = _signup(client, email="sessions-bob@example.com")
    alice_headers = _auth_headers(alice["session_token"])
    bob_headers = _auth_headers(bob["session_token"])

    alice_agent = _create_agent(client, alice_headers, brand_name="Alice Co")["agent_id"]
    bob_agent = _create_agent(client, bob_headers, brand_name="Bob Co")["agent_id"]

    with db_session() as db:
        alice_session = session_service.create_session(db, alice_agent)
        alice_sid = alice_session.session_id
        bob_session = session_service.create_session(db, bob_agent)
        bob_sid = bob_session.session_id

    alice_rows = client.get("/api/builder/sessions", headers=alice_headers).json()
    assert any(r["session_id"] == alice_sid for r in alice_rows)
    assert all(r["session_id"] != bob_sid for r in alice_rows)

    # Filtering by an agent_id that isn't theirs yields an empty list, not
    # someone else's data and not a 404 (this is a filtered list, not a
    # lookup-by-id -- the agent_id is just one more filter clause).
    filtered = client.get(
        "/api/builder/sessions", params={"agent_id": bob_agent}, headers=alice_headers
    ).json()
    assert filtered == []


def test_leads_endpoints_are_owner_scoped(client):
    alice = _signup(client, email="leads-alice@example.com")
    bob = _signup(client, email="leads-bob@example.com")
    alice_headers = _auth_headers(alice["session_token"])
    bob_headers = _auth_headers(bob["session_token"])

    alice_agent = _create_agent(client, alice_headers, brand_name="Alice Leads Co")["agent_id"]

    with db_session() as db:
        lead = lead_service.create_lead(
            db, agent_id=alice_agent, session_id=None, customer=None,
            name="Jordan", email="jordan@example.com", phone=None, source="widget",
        )
        lead_id = lead.id

    # Alice sees it in her list and stats, and can open/update it.
    alice_list = client.get("/api/builder/leads", headers=alice_headers).json()
    assert any(l["id"] == lead_id for l in alice_list)
    stats = client.get("/api/builder/leads/stats", headers=alice_headers).json()
    assert stats["total"] >= 1

    assert client.get(f"/api/builder/leads/{lead_id}", headers=alice_headers).status_code == 200
    patched = client.patch(
        f"/api/builder/leads/{lead_id}", json={"status": "contacted"}, headers=alice_headers
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "contacted"
    assert client.get(f"/api/builder/leads/{lead_id}/conversation", headers=alice_headers).status_code == 200

    # Bob never sees it, in the list or by id, and can't touch it.
    bob_list = client.get("/api/builder/leads", headers=bob_headers).json()
    assert all(l["id"] != lead_id for l in bob_list)
    assert client.get(f"/api/builder/leads/{lead_id}", headers=bob_headers).status_code == 404
    assert client.patch(
        f"/api/builder/leads/{lead_id}", json={"status": "converted"}, headers=bob_headers
    ).status_code == 404
    assert client.get(f"/api/builder/leads/{lead_id}/conversation", headers=bob_headers).status_code == 404


def test_customers_endpoint_scopes_counts_per_owner_not_globally(client):
    """The platform-admin customers view intentionally matches a visitor
    globally by email/phone across every tenant. The self-serve version
    must not inherit that -- if the same visitor talks to two different
    customers' agents, each customer may only see their own slice of that
    visitor's activity, never the other's session/lead count."""
    alice = _signup(client, email="customers-alice@example.com")
    bob = _signup(client, email="customers-bob@example.com")
    alice_headers = _auth_headers(alice["session_token"])
    bob_headers = _auth_headers(bob["session_token"])

    alice_agent = _create_agent(client, alice_headers, brand_name="Alice Customers Co")["agent_id"]
    bob_agent = _create_agent(client, bob_headers, brand_name="Bob Customers Co")["agent_id"]

    with db_session() as db:
        shared = customer_service.get_or_create_customer(db, name="Shared Visitor", email="shared@example.com")
        # This same visitor has one session with Alice's agent and two
        # with Bob's agent.
        s1 = session_service.create_session(db, alice_agent)
        s1.customer_id = shared.id
        s2 = session_service.create_session(db, bob_agent)
        s2.customer_id = shared.id
        s3 = session_service.create_session(db, bob_agent)
        s3.customer_id = shared.id
        db.commit()

    alice_customers = client.get("/api/builder/customers", headers=alice_headers).json()
    alice_row = next(r for r in alice_customers if r["email"] == "shared@example.com")
    assert alice_row["session_count"] == 1  # only Alice's own session with this visitor

    bob_customers = client.get("/api/builder/customers", headers=bob_headers).json()
    bob_row = next(r for r in bob_customers if r["email"] == "shared@example.com")
    assert bob_row["session_count"] == 2  # only Bob's own two sessions

    assert client.get("/api/builder/customers").status_code == 401
