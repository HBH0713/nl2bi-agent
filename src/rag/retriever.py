from typing import List, Dict, Optional
from src.rag.embedder import get_embedder
from src.db.chroma_client import get_or_create_collection
import structlog

logger = structlog.get_logger("retriever")


def hybrid_search(
    query: str,
    top_k: int = 10,
    table_filter: Optional[List[str]] = None,
) -> List[Dict]:
    """向量相似度检索，附带 metadata 过滤"""
    embedder = get_embedder()
    collection = get_or_create_collection("schema_embeddings")

    query_embedding = embedder.embed_single(query)

    where_filter = None
    if table_filter:
        where_filter = {"table_name": {"$in": table_filter}}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    documents = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            documents.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i] if results["documents"] else "",
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0.0,
            })

    logger.info("Hybrid search complete", query=query[:50], results_count=len(documents))
    return documents


def build_schema_context(query: str, top_tables: int = 5) -> str:
    """检索并组装 Schema Context 用于 NL2SQL Prompt"""
    results = hybrid_search(query, top_k=top_tables * 3)

    seen_tables = set()
    table_docs = []

    for doc in results:
        meta = doc["metadata"]
        if meta.get("type") == "table":
            table_name = meta.get("table_name", "")
            if table_name not in seen_tables:
                seen_tables.add(table_name)
                table_docs.append(doc)
                if len(table_docs) >= top_tables:
                    break

    business_terms = []
    for doc in results:
        if doc["metadata"].get("type") == "business_term":
            business_terms.append(doc["text"])

    context_parts = []

    if table_docs:
        context_parts.append("=== 相关数据表 ===")
        for doc in table_docs:
            context_parts.append(doc["text"])

    if business_terms:
        context_parts.append("\n=== 相关业务术语 ===")
        for term_text in business_terms[:5]:
            context_parts.append(f"- {term_text}")

    return "\n".join(context_parts)
