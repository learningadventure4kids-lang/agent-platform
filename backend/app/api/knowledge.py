"""Knowledge base management. Every route here is admin-authenticated --
this is the business owner managing their own agent's documents, not the
public widget. The public widget never sees this router at all; it only
ever reaches knowledge through the `search_knowledge_base` tool
(app/tools/knowledge.py), which resolves agent_id/knowledge_base_id
server-side from the validated agent token, never from anything the
browser sends.

Processing never happens inline here -- upload only validates, stores the
file, and enqueues a KnowledgeJob; worker/knowledge_worker.py does the
actual extract/chunk/embed/store work. See app/rag/ingestion/service.py
for that pipeline.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session as DBSession

from app.api.deps import Principal, get_admin_principal
from app.database.connection import get_db
from app.models.agent import Agent
from app.models.document import STATUS_PROCESSING, Document
from app.models.knowledge_job import JOB_TYPE_INGEST, JOB_TYPE_REPROCESS, STATUS_PENDING, KnowledgeJob
from app.rag import knowledge_base_service
from app.security.file_storage import FileValidationError
from app.services.document_upload_service import ingest_uploaded_document

logger = logging.getLogger("agent_platform.knowledge")

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _require_agent(db: DBSession, principal: Principal, agent_id: int) -> Agent:
    query = db.query(Agent).filter(Agent.id == agent_id)
    if not principal.is_platform_admin:
        query = query.filter(Agent.owner_user_id == principal.user_id)
    agent = query.first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


def _require_doc_owned(db: DBSession, principal: Principal, document_id: int) -> Document:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not principal.is_platform_admin:
        _require_agent(db, principal, doc.agent_id)  # 404s if not owned
    return doc


@router.get("/bases")
def list_knowledge_bases(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    agent = _require_agent(db, principal, agent_id)
    kb = knowledge_base_service.get_or_create_default(db, agent)
    db.commit()
    return [{"id": kb.id, "agent_id": kb.agent_id, "name": kb.name, "status": kb.status}]


@router.post("/bases")
def create_knowledge_base(
    agent_id: int, name: str = Form(...),
    db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal),
):
    from app.models.knowledge_base import KnowledgeBase

    agent = _require_agent(db, principal, agent_id)
    kb = KnowledgeBase(tenant_id=agent.tenant_id, agent_id=agent.id, name=name)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return {"id": kb.id, "agent_id": kb.agent_id, "name": kb.name, "status": kb.status}


@router.post("/upload")
async def upload_document(
    agent_id: int = Form(...),
    file: UploadFile = File(...),
    db: DBSession = Depends(get_db),
    principal: Principal = Depends(get_admin_principal),
):
    agent = _require_agent(db, principal, agent_id)

    contents = await file.read()
    try:
        result = ingest_uploaded_document(db, agent, file.filename or "upload", contents)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info(
        "document uploaded document_id=%s agent_id=%s filename=%s",
        result["document_id"], agent.id, file.filename,
    )
    return result


@router.get("")
def list_documents(
    agent_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    _require_agent(db, principal, agent_id)
    docs = (
        db.query(Document)
        .filter(Document.agent_id == agent_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        {
            "id": d.id,
            "agent_id": d.agent_id,
            "original_filename": d.original_filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "processing_error": d.processing_error,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
        }
        for d in docs
    ]


@router.get("/{document_id}")
def get_document(
    document_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    doc = _require_doc_owned(db, principal, document_id)
    return {
        "id": doc.id,
        "agent_id": doc.agent_id,
        "knowledge_base_id": doc.knowledge_base_id,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "status": doc.status,
        "processing_error": doc.processing_error,
        "chunk_count": doc.chunk_count,
        "created_at": doc.created_at,
        "updated_at": doc.updated_at,
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    from app.models.document_chunk import DocumentChunk

    doc = _require_doc_owned(db, principal, document_id)

    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    db.query(KnowledgeJob).filter(KnowledgeJob.document_id == document_id).delete()

    try:
        if doc.storage_path and os.path.exists(doc.storage_path):
            os.remove(doc.storage_path)
    except OSError:
        logger.warning("could not remove stored file for document_id=%s", document_id)

    db.delete(doc)
    db.commit()
    logger.info("document deleted document_id=%s", document_id)
    return {"deleted": True, "document_id": document_id}


@router.post("/{document_id}/reprocess")
def reprocess_document(
    document_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    doc = _require_doc_owned(db, principal, document_id)

    doc.status = STATUS_PROCESSING
    doc.processing_error = None

    job = KnowledgeJob(
        tenant_id=doc.tenant_id,
        agent_id=doc.agent_id,
        knowledge_base_id=doc.knowledge_base_id,
        document_id=doc.id,
        job_type=JOB_TYPE_REPROCESS,
        status=STATUS_PENDING,
    )
    db.add(job)
    db.commit()
    logger.info("document reprocess requested document_id=%s job_id=%s", document_id, job.id)
    return {"document_id": doc.id, "job_id": job.id, "status": doc.status}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int, db: DBSession = Depends(get_db), principal: Principal = Depends(get_admin_principal)
):
    job = db.query(KnowledgeJob).filter(KnowledgeJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not principal.is_platform_admin:
        _require_agent(db, principal, job.agent_id)  # 404s if not owned
    return {
        "id": job.id,
        "document_id": job.document_id,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "error_message": job.error_message,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
    }
