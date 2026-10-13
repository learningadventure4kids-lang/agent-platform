from app.database.connection import db_session
from app.models.document import STATUS_FAILED, STATUS_READY, Document
from app.models.document_chunk import DocumentChunk
from app.models.knowledge_job import STATUS_COMPLETED, STATUS_FAILED as JOB_FAILED, KnowledgeJob
from app.rag import knowledge_base_service
from app.rag.ingestion.service import process_job
from app.security.tokens import generate_token, hash_token


def _make_agent(db, key: str):
    from app.models.agent import Agent

    agent = Agent(
        agent_key=key,
        tenant_id=key,
        public_token_hash=hash_token(generate_token()),
        name="Test",
        brand_name="Test Co",
        system_prompt="x",
        welcome_message="hi",
    )
    db.add(agent)
    db.flush()
    return agent


def _make_document(db, agent, tmp_path, filename="doc.txt", content="Some useful content here.", file_type="txt"):
    kb = knowledge_base_service.get_or_create_default(db, agent)
    p = tmp_path / filename
    p.write_text(content)
    doc = Document(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        knowledge_base_id=kb.id,
        filename=filename,
        original_filename=filename,
        file_type=file_type,
        file_size=len(content),
        storage_path=str(p),
    )
    db.add(doc)
    db.flush()
    return doc, kb


def test_successful_ingestion_marks_ready_and_creates_chunks(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "ing-1")
        doc, kb = _make_document(db, agent, tmp_path, content="Our return policy allows 30 day returns. " * 20)
        job = KnowledgeJob(tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id, document_id=doc.id)
        db.add(job)
        db.flush()

        process_job(db, job, doc)

        assert doc.status == STATUS_READY
        assert doc.chunk_count > 0
        assert job.status == STATUS_COMPLETED
        assert job.progress == 100

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        assert len(chunks) == doc.chunk_count
        assert all(c.tenant_id == agent.tenant_id for c in chunks)
        assert all(c.agent_id == agent.id for c in chunks)


def test_failed_ingestion_marks_failed_with_error(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "ing-2")
        kb = knowledge_base_service.get_or_create_default(db, agent)
        doc = Document(
            tenant_id=agent.tenant_id,
            agent_id=agent.id,
            knowledge_base_id=kb.id,
            filename="missing.txt",
            original_filename="missing.txt",
            file_type="txt",
            file_size=1,
            storage_path=str(tmp_path / "does-not-exist.txt"),
        )
        db.add(doc)
        db.flush()
        job = KnowledgeJob(tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id, document_id=doc.id)
        db.add(job)
        db.flush()

        process_job(db, job, doc)

        assert doc.status == STATUS_FAILED
        assert doc.processing_error is not None
        assert job.status == JOB_FAILED
        assert job.error_message is not None


def test_reprocessing_does_not_duplicate_chunks(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "ing-3")
        doc, kb = _make_document(db, agent, tmp_path, content="Shipping takes 3 to 5 business days. " * 10)
        job1 = KnowledgeJob(tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id, document_id=doc.id)
        db.add(job1)
        db.flush()
        process_job(db, job1, doc)
        first_count = doc.chunk_count

        job2 = KnowledgeJob(tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id, document_id=doc.id)
        db.add(job2)
        db.flush()
        process_job(db, job2, doc)

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        assert len(chunks) == first_count  # not doubled
        assert doc.chunk_count == first_count


def test_ingestion_restart_safety_clears_partial_chunks(tmp_path):
    """Simulates a previous crashed attempt having already written some
    chunks for this document/job before failing -- re-running process_job
    must wipe those first, never append to them."""
    with db_session() as db:
        agent = _make_agent(db, "ing-4")
        doc, kb = _make_document(db, agent, tmp_path, content="Some content.")

        # Simulate leftover chunks from a crashed prior attempt.
        db.add(
            DocumentChunk(
                tenant_id=agent.tenant_id,
                agent_id=agent.id,
                knowledge_base_id=kb.id,
                document_id=doc.id,
                chunk_index=0,
                content="leftover chunk from a crashed run",
                chunk_metadata={},
                embedding=[0.1] * 32,
            )
        )
        db.flush()

        job = KnowledgeJob(tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id, document_id=doc.id)
        db.add(job)
        db.flush()
        process_job(db, job, doc)

        chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).all()
        assert not any("leftover chunk" in c.content for c in chunks)
        assert len(chunks) == doc.chunk_count
