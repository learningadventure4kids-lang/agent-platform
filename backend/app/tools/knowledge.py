"""The `search_knowledge_base` tool: the sole way the conversational agent
reaches the RAG system. The LLM only ever supplies a free-text `query` --
tenant_id, agent_id, and knowledge_base_id are resolved here from
`ToolContext.agent` (itself resolved server-side from the validated agent
token earlier in the request), never from anything the model or browser
could influence. This is what makes "Agent A can never retrieve Agent B's
knowledge" true by construction rather than by convention: there is no
parameter on this tool a compromised or confused LLM could set to point at
a different agent's knowledge base.
"""
from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.config import get_settings
from app.rag import knowledge_base_service
from app.rag.retrieval.retriever import KnowledgeRetriever
from app.tools.common import ToolContext


class SearchKnowledgeBaseArgs(BaseModel):
    query: str = Field(description="The visitor's question, in their own words")


def build_knowledge_tools(ctx: ToolContext) -> dict[str, StructuredTool]:
    def search_knowledge_base_fn(query: str) -> str:
        kb = knowledge_base_service.get_for_agent(ctx.db, ctx.agent.id)
        if kb is None:
            return "No knowledge base is configured for this business yet."

        settings = get_settings()
        retriever = KnowledgeRetriever(ctx.db)
        results = retriever.retrieve(
            tenant_id=ctx.agent.tenant_id,
            agent_id=ctx.agent.id,
            knowledge_base_id=kb.id,
            query=query,
            top_k=settings.TOP_K,
        )
        ctx.record("search_knowledge_base", f"{len(results)} chunks for query")

        if not results:
            return "No relevant information was found in the knowledge base for this question."

        # Deliberately returns only chunk content to the LLM -- no document
        # IDs, chunk IDs, or embedding/vector details, per the "don't
        # expose internal document metadata" rule in the RAG system prompt.
        return "\n\n---\n\n".join(r.content for r in results)

    return {
        "search_knowledge_base": StructuredTool.from_function(
            func=search_knowledge_base_fn,
            name="search_knowledge_base",
            description=(
                "Search this business's knowledge base (policies, FAQs, product/service "
                "descriptions, documentation) for information relevant to the visitor's "
                "question. Always use this for business-specific factual questions instead "
                "of answering from memory. Does not include live inventory, prices, or "
                "availability -- use the appropriate tool for those instead."
            ),
            args_schema=SearchKnowledgeBaseArgs,
        ),
    }
