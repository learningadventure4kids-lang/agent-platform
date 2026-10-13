from datetime import datetime, timedelta

from app.database.connection import db_session
from app.services import session_service


def test_create_session_requires_valid_token(client):
    resp = client.post("/api/session", json={"agent_token": "pub_bogus"})
    assert resp.status_code == 401


def test_create_session_with_valid_token(client, agent_tokens):
    token = agent_tokens["astrology"]["token"]
    resp = client.post("/api/session", json={"agent_token": token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"]
    assert body["agent"]["brand"] == "Astrology Advisor"
    assert body["messages"] == []


def test_get_session_not_found(client):
    resp = client.get("/api/session/does-not-exist")
    assert resp.status_code == 404


def test_session_messages_endpoint(client, agent_tokens):
    token = agent_tokens["kaur-jewellery"]["token"]
    created = client.post("/api/session", json={"agent_token": token}).json()
    sid = created["session_id"]

    with db_session() as db:
        session_service.save_message(db, sid, "user", "hello")
        session_service.save_message(db, sid, "assistant", "hi there")

    resp = client.get(f"/api/session/{sid}/messages")
    assert resp.status_code == 200
    roles = [m["role"] for m in resp.json()]
    assert roles == ["user", "assistant"]


def test_session_returning_visitor_flag(client, agent_tokens):
    token = agent_tokens["real-estate"]["token"]
    created = client.post("/api/session", json={"agent_token": token}).json()
    sid = created["session_id"]

    with db_session() as db:
        session_service.save_message(db, sid, "user", "hi")
        s = session_service.get_session(db, sid)
        s.last_activity_at = datetime.utcnow() - timedelta(minutes=10)

    resp = client.get(f"/api/session/{sid}")
    assert resp.json()["is_returning"] is True


def test_delete_session(client, agent_tokens):
    token = agent_tokens["kaur-jewellery"]["token"]
    created = client.post("/api/session", json={"agent_token": token}).json()
    sid = created["session_id"]
    resp = client.delete(f"/api/session/{sid}")
    assert resp.status_code == 200
    assert client.get(f"/api/session/{sid}").status_code == 404
