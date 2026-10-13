"""Shared "accept an uploaded file for an agent's knowledge base" logic,
used by both the admin knowledge API (app/api/knowledge.py) and the
self-serve builder API (app/api/builder.py) -- one implementation rather
than two copies that could drift. Validates and stores the file, then
enqueues a KnowledgeJob; the actual extract/chunk/embed/store pipeline
runs out-of-band in worker/knowledge_worker.py (see
app/rag/ingestion/service.py), never inline in a request handler."""
from __future__ import annotations

from sqlalchemy.orm import Session as DBSession

from app.models.agent import Agent
from app.models.document import STATUS_PROCESSING, Document
from app.models.knowledge_job import JOB_TYPE_INGEST, STATUS_PENDING, KnowledgeJob
from app.rag import knowledge_base_service
from app.security.file_storage import FileValidationError, build_storage_path, validate_upload


def ingest_uploaded_document(
    db: DBSession, agent: Agent, filename: str, contents: bytes, max_file_size: int | None = None
) -> dict:
    """Raises FileValidationError if the upload is rejected (bad
    extension/too large) -- callers turn that into an HTTP 400.

    `max_file_size` is forwarded to `validate_upload` so a caller (the
    self-serve builder) can enforce the uploading user's plan limit
    instead of the platform-wide default; the admin knowledge API leaves
    it unset and gets the default."""
    ext = validate_upload(filename or "upload", len(contents), max_size=max_file_size)
    stored_filename, storage_path = build_storage_path(agent.tenant_id, agent.id, ext)

    with open(storage_path, "wb") as f:
        f.write(contents)

    kb = knowledge_base_service.get_or_create_default(db, agent)

    document = Document(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        knowledge_base_id=kb.id,
        filename=stored_filename,
        original_filename=filename or stored_filename,
        file_type=ext,
        file_size=len(contents),
        storage_path=storage_path,
        status=STATUS_PROCESSING,
    )
    db.add(document)
    db.flush()

    job = KnowledgeJob(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        knowledge_base_id=kb.id,
        document_id=document.id,
        job_type=JOB_TYPE_INGEST,
        status=STATUS_PENDING,
    )
    db.add(job)
    db.commit()

    return {"document_id": document.id, "job_id": job.id, "status": document.status}
