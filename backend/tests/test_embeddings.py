import math

from app.rag.embeddings.service import DeterministicEmbeddingService, get_embedding_service


def test_deterministic_embedding_is_stable():
    svc = DeterministicEmbeddingService(dimension=16)
    v1 = svc.embed_text("hello world")
    v2 = svc.embed_text("hello world")
    assert v1 == v2


def test_deterministic_embedding_differs_by_text():
    svc = DeterministicEmbeddingService(dimension=16)
    assert svc.embed_text("hello") != svc.embed_text("goodbye")


def test_deterministic_embedding_correct_dimension():
    svc = DeterministicEmbeddingService(dimension=24)
    assert len(svc.embed_text("x")) == 24


def test_deterministic_embedding_is_unit_normalized():
    svc = DeterministicEmbeddingService(dimension=32)
    vec = svc.embed_text("some text")
    norm = math.sqrt(sum(v * v for v in vec))
    assert abs(norm - 1.0) < 1e-6


def test_embed_documents_matches_embed_text():
    svc = DeterministicEmbeddingService(dimension=8)
    docs = ["a", "b", "c"]
    assert svc.embed_documents(docs) == [svc.embed_text(d) for d in docs]


def test_get_embedding_service_returns_deterministic_in_test_env():
    # conftest.py sets EMBEDDING_PROVIDER=deterministic for the whole suite.
    svc = get_embedding_service()
    assert isinstance(svc, DeterministicEmbeddingService)
