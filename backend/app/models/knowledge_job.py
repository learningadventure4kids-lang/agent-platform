"""The job queue for document ingestion. Deliberately implemented as a
plain database table polled by worker/knowledge_worker.py rather than a
separate broker (Celery/Redis/etc.) -- this keeps local setup to "docker
compose up" with no extra infrastructure, while still being architecturally
a distinct background-processing step the chat API never touches directly.
Swapping in a real broker later only means changing how a job's status
transitions get triggered, not the API/worker contract."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base

JOB_TYPE_INGEST = "ingest"
JOB_TYPE_REPROCESS = "reprocess"

STATUS_PENDING = "PENDING"
STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"


class KnowledgeJob(Base):
    __tablename__ = "knowledge_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)

    job_type: Mapped[str] = mapped_column(String(20), default=JOB_TYPE_INGEST)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
