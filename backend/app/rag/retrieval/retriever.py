"""The single retrieval entry point for the whole platform (per the "one
shared RAG infrastructure" design principle -- there is no
jewellery_retriever.py / astrology_retriever.py).

`KnowledgeRetriever.retrieve` takes agent_id/knowledge_base_id as plain
Python arguments, not anything read from the request body -- callers
(app/tools/knowledge.py) always pass values already resolved server-side
from the validated agent token, never anything the browser sent directly.
Every query filters by tenant_id AND agent_id AND knowledge_base_id before
the similarity ORDER BY; there is no code path in this file that can run a
similarity search without all three filters applied.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session as DBSession

from app.models.document_chunk import DocumentChunk
from app.rag.embeddings.service import EmbeddingService, get_embedding_service


@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    distance: float  # lower = more similar (cosine distance)


class KnowledgeRetriever:
    def __init__(self, db: DBSession, embedding_service: EmbeddingService | None = None):
        self.db = db
        self.embedding_service = embedding_service or get_embedding_service()

    def retrieve(
        self,
        tenant_id: str,
        agent_id: int,
        knowledge_base_id: int,
        query: str,
        top_k: int = 4,
    ) -> list[RetrievedChunk]:
        query_vector = self.embedding_service.embed_text(query)
        distance_col = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

        rows = (
            self.db.query(DocumentChunk, distance_col)
            .filter(
                DocumentChunk.tenant_id == tenant_id,
                DocumentChunk.agent_id == agent_id,
                DocumentChunk.knowledge_base_id == knowledge_base_id,
            )
            .order_by(distance_col)
            .limit(top_k)
            .all()
        )

        # Belt-and-braces: even though the query above already filtered,
        # re-check every row before returning so a future refactor of the
        # query above can never silently widen access without tests
        # (test_tool_isolation.py / test_rag_isolation.py) catching it.
        safe_rows = [
            (chunk, distance)
            for chunk, distance in rows
            if chunk.tenant_id == tenant_id
            and chunk.agent_id == agent_id
            and chunk.knowledge_base_id == knowledge_base_id
        ]

        return [
            RetrievedChunk(content=chunk.content, metadata=chunk.chunk_metadata, distance=float(distance))
            for chunk, distance in safe_rows
        ]
