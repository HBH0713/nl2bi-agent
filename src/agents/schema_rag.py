from src.agents.state import AgentState
from src.rag.retriever import build_schema_context
import structlog

logger = structlog.get_logger("agent.schema_rag")


async def schema_rag_retriever(state: AgentState) -> dict:
    """Schema 检索节点 — 根据用户问题检索相关表结构"""
    query = state.get("user_query", "")

    if not query:
        return {"retrieved_schemas": [], "schema_context": ""}

    messages = state.get("messages", [])
    history_context = ""
    if messages:
        recent = [m for m in messages[-4:] if hasattr(m, "content")]
        history_context = " ".join(m.content for m in recent if m.content)

    search_query = f"{query} {history_context}" if history_context else query

    schema_context = build_schema_context(search_query, top_tables=5)

    logger.info("Schema RAG complete", query=query[:50], context_length=len(schema_context))

    return {
        "retrieved_schemas": [],
        "schema_context": schema_context,
    }
