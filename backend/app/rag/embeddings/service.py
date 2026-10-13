"""Embedding provider abstraction.

`EmbeddingService` is the only interface the rest of the RAG system talks
to (`embed_text` / `embed_documents`), so swapping providers -- a different
local model, or a hosted API -- never touches ingestion or retrieval code.

Two implementations ship:

- `OllamaEmbeddingService` (default, `EMBEDDING_PROVIDER=ollama`): calls a
  local Ollama embedding model (`EMBEDDING_MODEL`, e.g. "nomic-embed-text").
- `DeterministicEmbeddingService` (`EMBEDDING_PROVIDER=deterministic`): a
  dependency-free, seeded-hash embedding used by the test suite (and
  available as a offline fallback) so ingestion/retrieval logic can be
  exercised without a running Ollama instance. It is NOT semantically
  meaningful the way a real embedding is -- see its docstring.
"""
from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from functools import lru_cache

from app.config import get_settings


class EmbeddingService(ABC):
    dimension: int

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class OllamaEmbeddingService(EmbeddingService):
    def __init__(self, model: str, base_url: str, dimension: int):
        self.model = model
        self.base_url = base_url
        self.dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        # Imported lazily so the deterministic provider (used in tests /
        # offline dev) never requires langchain-ollama or a live server.
        from langchain_ollama import OllamaEmbeddings

        client = OllamaEmbeddings(model=self.model, base_url=self.base_url)
        return client.embed_query(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        from langchain_ollama import OllamaEmbeddings

        client = OllamaEmbeddings(model=self.model, base_url=self.base_url)
        return client.embed_documents(texts)


class DeterministicEmbeddingService(EmbeddingService):
    """Seeded-hash embedding: the same text always produces the same
    vector, and vectors are unit-normalized so cosine similarity behaves
    sensibly, but the vector space carries no real semantic meaning
    (two texts about the same topic in different words will NOT
    necessarily land close together). This exists purely so the ingestion
    pipeline, storage, and *tenant/agent filtering* in retrieval can be
    tested deterministically without a running Ollama instance -- it is
    not a substitute for a real embedding model in production."""

    def __init__(self, dimension: int):
        self.dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        vec = []
        seed = text.encode("utf-8")
        for i in range(self.dimension):
            h = hashlib.sha256(seed + i.to_bytes(4, "little")).digest()
            # Map first 8 bytes of the hash to a float in [-1, 1]
            val = int.from_bytes(h[:8], "little") / (2**64 - 1)
            vec.append(val * 2 - 1)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


@lru_cache
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    if settings.EMBEDDING_PROVIDER == "deterministic":
        return DeterministicEmbeddingService(dimension=settings.VECTOR_DIMENSION)
    return OllamaEmbeddingService(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        dimension=settings.VECTOR_DIMENSION,
    )
