from types import SimpleNamespace

import app.api.chat as chat_module


class FakeCtx:
    def __init__(self, customer=None, leads_created=None):
        self.customer = customer
        self.leads_created = leads_created or []
        self.tool_results = []


class FakeTurnResult:
    def __init__(self, assistant_text, ctx):
        self.assistant_text = assistant_text
        self.ctx = ctx
        self.state = {}


def test_chat_requires_valid_token(client):
    resp = client.post("/api/chat", json={"agent_token": "pub_bogus", "message": "hi"})
    assert resp.status_code == 401


def test_chat_creates_session_and_persists_messages(client, agent_tokens, monkeypatch):
    def fake_run_turn(**kwargs):
        return FakeTurnResult("Hello! How can I help?", FakeCtx())

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    token = agent_tokens["astrology"]["token"]
    resp = client.post("/api/chat", json={"agent_token": token, "message": "Hi there"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["agent"]["brand"] == "Astrology Advisor"
    assert body["response"] == "Hello! How can I help?"
    assert body["lead_created"] is False

    history = client.get(f"/api/session/{body['session_id']}/messages").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "Hi there"


def test_chat_reports_lead_created(client, agent_tokens, monkeypatch):
    fake_lead = SimpleNamespace(id=1, status="qualified")

    def fake_run_turn(**kwargs):
        return FakeTurnResult("All set!", FakeCtx(leads_created=[fake_lead]))

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    token = agent_tokens["kaur-jewellery"]["token"]
    resp = client.post("/api/chat", json={"agent_token": token, "message": "Yes, go ahead"})
    assert resp.json()["lead_created"] is True


def test_chat_falls_back_gracefully_on_failure(client, agent_tokens, monkeypatch):
    def failing_run_turn(**kwargs):
        raise RuntimeError("Ollama unavailable")

    monkeypatch.setattr(chat_module, "run_turn", failing_run_turn)

    token = agent_tokens["real-estate"]["token"]
    resp = client.post("/api/chat", json={"agent_token": token, "message": "Hello?"})
    assert resp.status_code == 200
    assert "temporary problem" in resp.json()["response"]


def test_session_id_from_different_agent_is_not_reused(client, agent_tokens, monkeypatch):
    def fake_run_turn(**kwargs):
        return FakeTurnResult("ok", FakeCtx())

    monkeypatch.setattr(chat_module, "run_turn", fake_run_turn)

    kaur_token = agent_tokens["kaur-jewellery"]["token"]
    astrology_token = agent_tokens["astrology"]["token"]

    kaur_session = client.post(
        "/api/chat", json={"agent_token": kaur_token, "message": "hi"}
    ).json()["session_id"]

    # Reusing Kaur's session_id while authenticating as the astrology agent
    # must NOT attach astrology messages to Kaur's session.
    resp = client.post(
        "/api/chat",
        json={"agent_token": astrology_token, "session_id": kaur_session, "message": "hi"},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] != kaur_session
