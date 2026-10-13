from app.database.connection import db_session
from app.models.document import Document
from app.models.knowledge_job import KnowledgeJob
from app.models.session import Session as SessionModel
from app.rag import knowledge_base_service
from app.rag.ingestion.service import process_job
from app.security.tokens import generate_token, hash_token
from app.tools.common import ToolContext
from app.tools.knowledge import build_knowledge_tools


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


def test_tool_reports_no_knowledge_base_when_none_configured():
    with db_session() as db:
        agent = _make_agent(db, "tool-no-kb")
        session = SessionModel(agent_id=agent.id)
        db.add(session)
        db.flush()
        ctx = ToolContext(db=db, agent=agent, session=session, customer=None)
        tools = build_knowledge_tools(ctx)
        result = tools["search_knowledge_base"].invoke({"query": "anything"})
        assert "No knowledge base is configured" in result


def test_tool_returns_relevant_content_without_leaking_metadata(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "tool-with-kb")
        kb = knowledge_base_service.get_or_create_default(db, agent)

        p = tmp_path / "secret-filename-should-not-leak.txt"
        p.write_text("Our support hours are 9am to 5pm, Monday through Friday. " * 5)
        doc = Document(
            tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id,
            filename="stored.txt", original_filename="secret-filename-should-not-leak.txt",
            file_type="txt", file_size=10, storage_path=str(p),
        )
        db.add(doc)
        db.flush()
        job = KnowledgeJob(tenant_id=agent.tenant_id, agent_id=agent.id, knowledge_base_id=kb.id, document_id=doc.id)
        db.add(job)
        db.flush()
        process_job(db, job, doc)

        session = SessionModel(agent_id=agent.id)
        db.add(session)
        db.flush()
        ctx = ToolContext(db=db, agent=agent, session=session, customer=None)
        tools = build_knowledge_tools(ctx)
        result = tools["search_knowledge_base"].invoke({"query": "What are your support hours?"})

        assert "9am to 5pm" in result
        assert "secret-filename-should-not-leak" not in result
        assert "stored.txt" not in result


def test_tool_reports_no_results_gracefully(tmp_path):
    with db_session() as db:
        agent = _make_agent(db, "tool-empty-kb")
        knowledge_base_service.get_or_create_default(db, agent)
        session = SessionModel(agent_id=agent.id)
        db.add(session)
        db.flush()
        ctx = ToolContext(db=db, agent=agent, session=session, customer=None)
        tools = build_knowledge_tools(ctx)
        result = tools["search_knowledge_base"].invoke({"query": "anything at all"})
        assert "No relevant information" in result
