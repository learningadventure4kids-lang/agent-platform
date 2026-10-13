from app.database.connection import db_session
from app.models.document import Document
from app.models.knowledge_job import KnowledgeJob
from app.rag import knowledge_base_service
from app.rag.ingestion.service import process_job
from app.rag.retrieval.retriever import KnowledgeRetriever
from app.security.tokens import generate_token, hash_token


def _make_agent(db, key: str):
    from app.models.agent import Agent

    agent = Agent(
        agent_key=key,
        tenant_id=key,
        public_token_hash=hash_token(generate_token()),
        name="Test",
        brand_name=key,
        system_prompt="x",
        welcome_message="hi",
    )
    db.add(agent)
    db.flush()
    return agent


def _ingest(db, agent, tmp_path, filename, content):
    kb = knowledge_base_service.get_or_create_default(db, agent)
    p = tmp_path / filename
    p.write_text(content)
    doc = Document(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        knowledge_base_id=kb.id,
        filename=filename,
        original_filename=filename,
        file_type="txt",
        file_size=len(content),
        storage_path=str(p),
    )
    db.add(doc)
    db.flush()
    job = KnowledgeJob(tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id, document_id=doc.id)
    db.add(job)
    db.flush()
    process_job(db, job, doc)
    return doc, kb


def test_retrieval_returns_relevant_chunks(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "retr-1")
        doc, kb = _ingest(
            db, agent, tmp_path, "policy.txt",
            "Our jewellery return policy allows returns within 30 days with a receipt. " * 5,
        )
        retriever = KnowledgeRetriever(db)
        results = retriever.retrieve(agent.tenant_id, agent.id, kb.id, "What is your return policy?", top_k=3)
        assert len(results) > 0
        assert any("return" in r.content.lower() for r in results)


def test_retrieval_respects_top_k(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "retr-2")
        long_content = " ".join(f"Sentence {i} about topic {i}." for i in range(200))
        doc, kb = _ingest(db, agent, tmp_path, "big.txt", long_content)
        assert doc.chunk_count > 5  # sanity: enough chunks exist to actually test top_k
        retriever = KnowledgeRetriever(db)
        results = retriever.retrieve(agent.tenant_id, agent.id, kb.id, "topic 5", top_k=2)
        assert len(results) <= 2


def test_retrieval_empty_knowledge_base_returns_nothing(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "retr-3")
        kb = knowledge_base_service.get_or_create_default(db, agent)
        retriever = KnowledgeRetriever(db)
        results = retriever.retrieve(agent.tenant_id, agent.id, kb.id, "anything", top_k=4)
        assert results == []


def test_CRITICAL_agent_a_never_retrieves_agent_b_knowledge(tmp_path):
    """The critical isolation test: Agent A (jewellery) and Agent B (real
    estate) both have documents. Asking Agent A a question that is only
    answerable from Agent B's content must return nothing from Agent B --
    not even as a fallback when Agent A's own knowledge doesn't match."""
    with db_session() as db:
        agent_a = _make_agent(db, "jewellery-isolation")
        agent_b = _make_agent(db, "realestate-isolation")

        _ingest(
            db, agent_a, tmp_path, "jewellery-return-policy.txt",
            "Our jewellery return policy allows returns within 30 days of purchase with the original receipt. " * 5,
        )
        _ingest(
            db, agent_b, tmp_path, "mortgage-policy.txt",
            "Our real estate mortgage policy requires a 20 percent down payment for investment properties. " * 5,
        )

        kb_a = knowledge_base_service.get_for_agent(db, agent_a.id)
        kb_b = knowledge_base_service.get_for_agent(db, agent_b.id)
        retriever = KnowledgeRetriever(db)

        # 1. Agent A asked its own domain's question -> gets its own content.
        own_results = retriever.retrieve(agent_a.tenant_id, agent_a.id, kb_a.id, "What is your jewellery return policy?", top_k=4)
        assert len(own_results) > 0
        assert all("mortgage" not in r.content.lower() for r in own_results)

        # 2. Agent A asked Agent B's domain question -> must NOT leak Agent B's content.
        cross_results = retriever.retrieve(agent_a.tenant_id, agent_a.id, kb_a.id, "What is the real estate mortgage policy?", top_k=4)
        assert all("mortgage" not in r.content.lower() for r in cross_results)
        assert all("20 percent down payment" not in r.content.lower() for r in cross_results)

        # 3. Same check in the other direction, for good measure.
        agent_b_results = retriever.retrieve(agent_b.tenant_id, agent_b.id, kb_b.id, "What is your jewellery return policy?", top_k=4)
        assert all("jewellery" not in r.content.lower() for r in agent_b_results)

        # 4. Direct proof at the storage layer: every chunk stored for
        # agent_a's tenant/agent/kb triple is genuinely agent_a's, regardless
        # of what any particular query happens to return.
        from app.models.document_chunk import DocumentChunk

        agent_a_chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.tenant_id == agent_a.tenant_id,
                DocumentChunk.agent_id == agent_a.id,
                DocumentChunk.knowledge_base_id == kb_a.id,
            )
            .all()
        )
        assert all(c.agent_id == agent_a.id for c in agent_a_chunks)
        assert all("mortgage" not in c.content.lower() for c in agent_a_chunks)


def test_wrong_knowledge_base_id_for_agent_returns_nothing(tmp_path):
    """Even if a caller passed a knowledge_base_id belonging to a DIFFERENT
    agent (which should never happen given the server always derives it
    from the resolved agent -- this proves the filter itself is airtight
    regardless), no cross-agent chunk is ever returned."""
    with db_session() as db:
        agent_a = _make_agent(db, "kb-mismatch-a")
        agent_b = _make_agent(db, "kb-mismatch-b")
        _ingest(db, agent_b, tmp_path, "secret.txt", "Agent B's confidential pricing information. " * 5)
        kb_b = knowledge_base_service.get_for_agent(db, agent_b.id)

        retriever = KnowledgeRetriever(db)
        # Attacker-style call: agent_a's tenant/agent id, but agent_b's kb id.
        results = retriever.retrieve(agent_a.tenant_id, agent_a.id, kb_b.id, "pricing information", top_k=4)
        assert results == []
