"""Per-plan document upload limits for the self-serve builder
(app/billing/plans.py, enforced in app/api/builder.py's upload route).
Free: 3 documents per agent, 5 MB each. Plus: higher limits, settable
today only by a platform operator via app/api/admin_users.py (no
payment processor wired up yet)."""
from __future__ import annotations

import io

from app.billing.plans import PLAN_LIMITS, PLAN_FREE, PLAN_PLUS
from app.database.connection import db_session
from app.models.user import User


def _signup(client, email="plan-test@example.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "correct horse battery staple", "name": "Founder"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_agent(client, headers, brand_name="Plan Test Co"):
    resp = client.post(
        "/api/builder/agents",
        json={"persona_key": "custom", "name": "A", "brand_name": brand_name},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["agent_id"]


def _upload(client, headers, agent_id, filename="doc.txt", content=b"hello world", mime="text/plain"):
    return client.post(
        f"/api/builder/agents/{agent_id}/documents",
        files={"file": (filename, io.BytesIO(content), mime)},
        headers=headers,
    )


def test_new_signup_defaults_to_free_plan(client):
    auth = _signup(client, email="defaults-to-free@example.com")
    assert auth["user"]["plan"] == PLAN_FREE


def test_my_plan_endpoint_reports_free_limits(client):
    auth = _signup(client, email="my-plan-free@example.com")
    resp = client.get("/api/builder/me/plan", headers=_auth_headers(auth["session_token"]))
    assert resp.status_code == 200
    body = resp.json()
    assert body["plan"] == PLAN_FREE
    assert body["max_documents_per_agent"] == PLAN_LIMITS[PLAN_FREE]["max_documents_per_agent"]
    assert body["max_file_size_mb"] == PLAN_LIMITS[PLAN_FREE]["max_file_size_bytes"] / (1024 * 1024)


def test_free_plan_blocks_the_fourth_document(client):
    auth = _signup(client, email="free-doc-limit@example.com")
    headers = _auth_headers(auth["session_token"])
    agent_id = _create_agent(client, headers, brand_name="Free Doc Limit Co")

    max_docs = PLAN_LIMITS[PLAN_FREE]["max_documents_per_agent"]
    for i in range(max_docs):
        resp = _upload(client, headers, agent_id, filename=f"doc{i}.txt")
        assert resp.status_code == 200, resp.text

    blocked = _upload(client, headers, agent_id, filename="one-too-many.txt")
    assert blocked.status_code == 403
    assert "limit" in blocked.json()["detail"].lower()


def test_free_plan_rejects_a_file_over_5mb(client):
    auth = _signup(client, email="free-size-limit@example.com")
    headers = _auth_headers(auth["session_token"])
    agent_id = _create_agent(client, headers, brand_name="Free Size Limit Co")

    oversized = b"x" * (6 * 1024 * 1024)  # 6 MB > the free plan's 5 MB cap
    resp = _upload(client, headers, agent_id, filename="big.txt", content=oversized)
    assert resp.status_code == 400
    assert "too large" in resp.json()["detail"].lower()


def test_free_plan_accepts_a_file_under_5mb(client):
    auth = _signup(client, email="free-size-ok@example.com")
    headers = _auth_headers(auth["session_token"])
    agent_id = _create_agent(client, headers, brand_name="Free Size Ok Co")

    ok_size = b"x" * (4 * 1024 * 1024)  # under the 5 MB cap
    resp = _upload(client, headers, agent_id, filename="ok.txt", content=ok_size)
    assert resp.status_code == 200, resp.text


def test_plus_plan_allows_more_documents_and_larger_files(client):
    auth = _signup(client, email="plus-plan@example.com")
    headers = _auth_headers(auth["session_token"])
    agent_id = _create_agent(client, headers, brand_name="Plus Plan Co")

    with db_session() as db:
        user = db.query(User).filter(User.email == "plus-plan@example.com").first()
        user.plan = PLAN_PLUS
        db.commit()

    free_max = PLAN_LIMITS[PLAN_FREE]["max_documents_per_agent"]
    # More documents than the free plan would ever allow.
    for i in range(free_max + 2):
        resp = _upload(client, headers, agent_id, filename=f"plus-doc{i}.txt")
        assert resp.status_code == 200, resp.text

    # And a file bigger than the free plan's cap but within the plus plan's.
    bigger = b"x" * (10 * 1024 * 1024)
    resp = _upload(client, headers, agent_id, filename="plus-big.txt", content=bigger)
    assert resp.status_code == 200, resp.text


def test_document_limit_is_per_agent_not_per_account(client):
    """A free-plan customer with two agents gets 3 documents on EACH,
    not 3 total -- the knowledge base is scoped per agent, so the quota
    is too."""
    auth = _signup(client, email="per-agent-limit@example.com")
    headers = _auth_headers(auth["session_token"])
    agent_a = _create_agent(client, headers, brand_name="Agent A Co")
    agent_b = _create_agent(client, headers, brand_name="Agent B Co")

    max_docs = PLAN_LIMITS[PLAN_FREE]["max_documents_per_agent"]
    for i in range(max_docs):
        assert _upload(client, headers, agent_a, filename=f"a{i}.txt").status_code == 200
    for i in range(max_docs):
        assert _upload(client, headers, agent_b, filename=f"b{i}.txt").status_code == 200

    assert _upload(client, headers, agent_a, filename="a-overflow.txt").status_code == 403
    assert _upload(client, headers, agent_b, filename="b-overflow.txt").status_code == 403


def test_xlsx_upload_is_accepted_and_ingested(client):
    """xlsx wasn't previously in ALLOWED_FILE_EXTENSIONS / the loader
    registry at all -- this proves both the extension allow-list and the
    new XLSXLoader (app/rag/ingestion/loaders/xlsx.py) actually work end
    to end, not just that the upload route accepts the extension."""
    from openpyxl import Workbook

    auth = _signup(client, email="xlsx-upload@example.com")
    headers = _auth_headers(auth["session_token"])
    agent_id = _create_agent(client, headers, brand_name="Xlsx Upload Co")

    wb = Workbook()
    ws = wb.active
    ws.title = "FAQ"
    ws.append(["Question", "Answer"])
    ws.append(["What are your hours?", "9am to 5pm, Monday through Friday."])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    resp = _upload(
        client, headers, agent_id, filename="faq.xlsx", content=buf.read(),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "PROCESSING"

    from app.rag.ingestion.loaders import get_loader
    from app.models.document import Document

    with db_session() as db:
        doc = db.query(Document).filter(Document.id == resp.json()["document_id"]).first()
        assert doc.file_type == "xlsx"
        pages = get_loader("xlsx").load(doc.storage_path)
    assert any("9am to 5pm" in p.text for p in pages)
