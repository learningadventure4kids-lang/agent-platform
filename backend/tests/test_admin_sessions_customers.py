from app.database.connection import db_session
from app.services import customer_service, session_service


def test_admin_sessions_requires_auth(client):
    assert client.get("/api/admin/sessions").status_code == 401


def test_admin_sessions_lists_agent_and_message_count(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["astrology"]["id"]
    with db_session() as db:
        session = session_service.create_session(db, agent_id)
        sid = session.session_id
        session_service.save_message(db, sid, "user", "hi")
        session_service.save_message(db, sid, "assistant", "hello")

    resp = client.get("/api/admin/sessions", params={"agent_id": agent_id}, headers=admin_headers)
    assert resp.status_code == 200
    row = next(r for r in resp.json() if r["session_id"] == sid)
    assert row["agent_key"] == "astrology"
    assert row["message_count"] == 2


def test_admin_customers_requires_auth(client):
    assert client.get("/api/admin/customers").status_code == 401


def test_admin_customers_lists_counts(client, admin_headers):
    with db_session() as db:
        customer_service.get_or_create_customer(db, name="Zed", email="zed@example.com")

    resp = client.get("/api/admin/customers", headers=admin_headers)
    assert resp.status_code == 200
    row = next(r for r in resp.json() if r["email"] == "zed@example.com")
    assert row["name"] == "Zed"
    assert "session_count" in row and "lead_count" in row
