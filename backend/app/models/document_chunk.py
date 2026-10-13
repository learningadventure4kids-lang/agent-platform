"""A single embedded chunk of a document. This is the table vector search
actually runs against -- every query MUST filter by tenant_id/agent_id
(and usually knowledge_base_id) before the similarity ORDER BY, which is
exactly what app/rag/retrieval/retriever.py does and never lets the caller
bypass.
"""
from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.config import get_settings
from app.database.connection import Base

_VECTOR_DIM = get_settings().VECTOR_DIMENSION


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_chunks_tenant_agent_kb", "tenant_id", "agent_id", "knowledge_base_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(80), index=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)

    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list] = mapped_column(Vector(_VECTOR_DIM))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
