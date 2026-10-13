"""A single uploaded (or eventually crawled/synced) knowledge source.
`source_type` is included now even though only "document" is implemented,
so websites/FAQs/DB-backed sources can be added later without a schema
change (see app/rag/ingestion/loaders/ for the loader abstraction that
source_type maps to)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base

# document | website | faq | database | api -- only "document" is
# implemented by the ingestion pipeline today.
SOURCE_TYPE_DOCUMENT = "document"

STATUS_PENDING = "PENDING"
STATUS_PROCESSING = "PROCESSING"
STATUS_READY = "READY"
STATUS_FAILED = "FAILED"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)

    source_type: Mapped[str] = mapped_column(String(20), default=SOURCE_TYPE_DOCUMENT)
    filename: Mapped[str] = mapped_column(String(255))  # sanitized, stored-on-disk name
    original_filename: Mapped[str] = mapped_column(String(255))  # as uploaded, for display only
    file_type: Mapped[str] = mapped_column(String(20))  # pdf | docx | txt | csv | json | md | xlsx
    file_size: Mapped[int] = mapped_column(BigInteger)
    storage_path: Mapped[str] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), default=STATUS_PENDING, index=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
