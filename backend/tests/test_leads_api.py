from app.database.connection import db_session
from app.models.lead import Lead


def _make_lead(agent_id, email="lead@example.com", status="new"):
    with db_session() as db:
        lead = Lead(
            agent_id=agent_id,
            session_id="test-session",
            name="Test Lead",
            email=email,
            source="widget",
            status=status,
            score=70,
            metadata_json={"note": "test"},
        )
        db.add(lead)
        db.flush()
        return lead.id


def test_leads_require_admin_auth(client):
    assert client.get("/api/admin/leads").status_code == 401


def test_list_and_filter_leads(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["kaur-jewellery"]["id"]
    _make_lead(agent_id, email="a@example.com")

    resp = client.get("/api/admin/leads", params={"agent_id": agent_id}, headers=admin_headers)
    assert resp.status_code == 200
    assert all(l["agent_id"] == agent_id for l in resp.json())


def test_lead_stats(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["astrology"]["id"]
    _make_lead(agent_id, email="b@example.com", status="qualified")

    resp = client.get("/api/admin/leads/stats", params={"agent_id": agent_id}, headers=admin_headers)
    body = resp.json()
    assert body["total"] >= 1
    assert body["qualified"] >= 1


def test_lead_detail_and_update(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["real-estate"]["id"]
    lead_id = _make_lead(agent_id, email="c@example.com")

    detail = client.get(f"/api/admin/leads/{lead_id}", headers=admin_headers)
    assert detail.status_code == 200

    patched = client.patch(
        f"/api/admin/leads/{lead_id}",
        json={"status": "contacted", "notes": "Called, left voicemail"},
        headers=admin_headers,
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "contacted"
    assert patched.json()["metadata_json"]["admin_notes"] == "Called, left voicemail"


def test_lead_not_found(client, admin_headers):
    assert client.get("/api/admin/leads/999999", headers=admin_headers).status_code == 404
