import io
import time

from app.database.connection import db_session


def _get_agent_id(client, admin_headers, agent_key):
    resp = client.get("/api/admin/agents", headers=admin_headers)
    return next(a["id"] for a in resp.json() if a["agent_key"] == agent_key)


def test_knowledge_endpoints_require_admin_auth(client):
    assert client.get("/api/knowledge", params={"agent_id": 1}).status_code == 401
    assert client.post("/api/knowledge/upload", data={"agent_id": 1}).status_code == 401


def test_upload_creates_document_and_job(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["kaur-jewellery"]["id"]
    file_content = b"Our jewellery return policy allows returns within 30 days."
    resp = client.post(
        "/api/knowledge/upload",
        data={"agent_id": str(agent_id)},
        files={"file": ("return-policy.txt", io.BytesIO(file_content), "text/plain")},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PROCESSING"
    assert body["document_id"]
    assert body["job_id"]


def test_upload_rejects_disallowed_extension(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["kaur-jewellery"]["id"]
    resp = client.post(
        "/api/knowledge/upload",
        data={"agent_id": str(agent_id)},
        files={"file": ("virus.exe", io.BytesIO(b"not allowed"), "application/octet-stream")},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_upload_rejects_unknown_agent(client, admin_headers):
    resp = client.post(
        "/api/knowledge/upload",
        data={"agent_id": "999999"},
        files={"file": ("a.txt", io.BytesIO(b"content"), "text/plain")},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_list_and_get_and_delete_document(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["astrology"]["id"]
    upload = client.post(
        "/api/knowledge/upload",
        data={"agent_id": str(agent_id)},
        files={"file": ("faq.txt", io.BytesIO(b"Some FAQ content."), "text/plain")},
        headers=admin_headers,
    ).json()
    doc_id = upload["document_id"]

    listing = client.get("/api/knowledge", params={"agent_id": agent_id}, headers=admin_headers)
    assert any(d["id"] == doc_id for d in listing.json())

    detail = client.get(f"/api/knowledge/{doc_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["original_filename"] == "faq.txt"

    deleted = client.delete(f"/api/knowledge/{doc_id}", headers=admin_headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/knowledge/{doc_id}", headers=admin_headers).status_code == 404


def test_delete_document_removes_chunks(client, admin_headers, agent_tokens):
    from app.models.document_chunk import DocumentChunk
    from app.models.knowledge_job import KnowledgeJob
    from app.rag.ingestion.service import process_job
    from app.models.document import Document

    agent_id = agent_tokens["real-estate"]["id"]
    upload = client.post(
        "/api/knowledge/upload",
        data={"agent_id": str(agent_id)},
        files={"file": ("props.txt", io.BytesIO(b"Some property information here."), "text/plain")},
        headers=admin_headers,
    ).json()
    doc_id = upload["document_id"]
    job_id = upload["job_id"]

    with db_session() as db:
        job = db.query(KnowledgeJob).filter(KnowledgeJob.id == job_id).first()
        doc = db.query(Document).filter(Document.id == doc_id).first()
        process_job(db, job, doc)
        assert doc.chunk_count > 0

    client.delete(f"/api/knowledge/{doc_id}", headers=admin_headers)

    with db_session() as db:
        remaining = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc_id).count()
        assert remaining == 0


def test_reprocess_document(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["kaur-jewellery"]["id"]
    upload = client.post(
        "/api/knowledge/upload",
        data={"agent_id": str(agent_id)},
        files={"file": ("catalogue.txt", io.BytesIO(b"Catalogue content."), "text/plain")},
        headers=admin_headers,
    ).json()
    doc_id = upload["document_id"]

    resp = client.post(f"/api/knowledge/{doc_id}/reprocess", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "PROCESSING"
    assert body["job_id"] != upload["job_id"]


def test_job_status_endpoint(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["astrology"]["id"]
    upload = client.post(
        "/api/knowledge/upload",
        data={"agent_id": str(agent_id)},
        files={"file": ("info.txt", io.BytesIO(b"Some info."), "text/plain")},
        headers=admin_headers,
    ).json()
    job_resp = client.get(f"/api/knowledge/jobs/{upload['job_id']}", headers=admin_headers)
    assert job_resp.status_code == 200
    assert job_resp.json()["status"] == "PENDING"


def test_knowledge_bases_endpoint_auto_creates_default(client, admin_headers, agent_tokens):
    agent_id = agent_tokens["real-estate"]["id"]
    resp = client.get("/api/knowledge/bases", params={"agent_id": agent_id}, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
