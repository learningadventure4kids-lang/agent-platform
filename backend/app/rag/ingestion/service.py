"""The document ingestion pipeline. Called by worker/knowledge_worker.py
(never by the chat or upload API directly -- see the module docstring in
that file for why). Restart-safe: re-running the same job always deletes
any chunks that job might have partially written before retrying, so a
crash mid-ingestion can never leave duplicate or orphaned chunks.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.models.document import STATUS_FAILED, STATUS_READY, Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_job import (
    STATUS_COMPLETED,
    STATUS_FAILED as JOB_FAILED,
    STATUS_RUNNING,
    KnowledgeJob,
)
from app.rag.chunking.splitter import split_pages
from app.rag.embeddings.service import get_embedding_service
from app.rag.ingestion.loaders import LoaderError, get_loader

logger = logging.getLogger("agent_platform.ingestion")


def _delete_existing_chunks(db: DBSession, document_id: int) -> None:
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    db.flush()


def process_job(db: DBSession, job: KnowledgeJob, document: Document) -> None:
    """Runs one ingestion job to completion (or failure), committing its
    own transaction. Never raises -- all failures are captured onto the
    job/document rows so the worker loop can simply move on."""
    job.status = STATUS_RUNNING
    job.started_at = datetime.utcnow()
    job.progress = 0
    db.commit()

    try:
        logger.info(
            "ingestion started document_id=%s agent_id=%s file_type=%s",
            document.id, document.agent_id, document.file_type,
        )

        # Restart-safety: wipe any chunks a previous, crashed attempt at
        # this same job/document might have already written.
        _delete_existing_chunks(db, document.id)

        loader = get_loader(document.file_type)
        pages = loader.load(document.storage_path)
        job.progress = 20
        db.commit()

        chunks = split_pages(pages)
        if not chunks:
            raise LoaderError("Document produced no chunks after splitting.")
        job.progress = 40
        db.commit()

        embedding_service = get_embedding_service()
        t0 = time.monotonic()
        vectors = embedding_service.embed_documents([c.content for c in chunks])
        embed_seconds = time.monotonic() - t0
        job.progress = 80
        db.commit()

        for chunk, vector in zip(chunks, vectors):
            metadata = {
                "filename": document.original_filename,
                "chunk_index": chunk.chunk_index,
                "document_id": document.id,
                "agent_id": document.agent_id,
                **chunk.metadata,
            }
            db.add(
                DocumentChunk(
                    tenant_id=document.tenant_id,
                    agent_id=document.agent_id,
                    knowledge_base_id=document.knowledge_base_id,
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    chunk_metadata=metadata,
                    embedding=vector,
                )
            )

        document.chunk_count = len(chunks)
        document.status = STATUS_READY
        document.processing_error = None

        job.status = STATUS_COMPLETED
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()

        logger.info(
            "ingestion completed document_id=%s chunks=%d embed_seconds=%.2f",
            document.id, len(chunks), embed_seconds,
        )

    except LoaderError as exc:
        db.rollback()
        _mark_failed(db, job, document, str(exc))
    except Exception as exc:  # noqa: BLE001 -- ingestion must never crash the worker
        db.rollback()
        logger.exception("ingestion failed document_id=%s", document.id)
        _mark_failed(db, job, document, f"Unexpected error: {exc}")


def _mark_failed(db: DBSession, job: KnowledgeJob, document: Document, message: str) -> None:
    document.status = STATUS_FAILED
    document.processing_error = message
    job.status = JOB_FAILED
    job.error_message = message
    job.completed_at = datetime.utcnow()
    db.commit()
    logger.warning("ingestion failed document_id=%s error=%s", document.id, message)
