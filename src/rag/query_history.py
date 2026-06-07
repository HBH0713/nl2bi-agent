"""
查询历史匹配模块 — 参考 WrenAI historical_question_retrieval 设计

每次成功执行 SQL 后，将 (问题, SQL) 存入 ChromaDB。
下次用户提问时，先做语义相似度匹配，命中则直接复用缓存的 SQL。
"""
from typing import Dict, List, Optional, Any
import datetime
from chromadb import Collection

from src.db.chroma_client import get_chroma_client
from src.config import get_settings
from src.rag.embedder import get_embedder
import structlog

logger = structlog.get_logger("query_history")

COLLECTION_NAME = "query_history"


def get_history_collection() -> Collection:
    """获取或创建查询历史集合"""
    client = get_chroma_client()
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        logger.info("creating_query_history_collection")
        coll = client.create_collection(
            name=COLLECTION_NAME,
            metadata={
                "description": "Successful NL2SQL query history for semantic matching",
                "hnsw:space": "cosine",
            },
        )
        return coll


def add_to_history(
    query: str,
    sql: str,
    explanation: str = "",
    row_count: int = 0,
    tables_used: List[str] = None,
    interpretation: str = "",
    highlights: List[str] = None,
    chart_suggestion: Dict = None,
    follow_up_questions: List[str] = None,
) -> str:
    """将成功执行的完整查询结果存入历史（含解释和可视化建议）"""
    coll = get_history_collection()
    embedder = get_embedder()

    doc_id = f"hist_{hash(query)}_{datetime.datetime.now().timestamp():.0f}"

    # 用 | 分隔符存储列表字段（ChromaDB metadata 只支持简单类型）
    metadata = {
        "sql": sql,
        "explanation": explanation,
        "row_count": row_count,
        "tables_used": ",".join(tables_used) if tables_used else "",
        "interpretation": interpretation,
        "highlights": "|".join(highlights) if highlights else "",
        "chart_type": chart_suggestion.get("type", "") if chart_suggestion else "",
        "chart_reason": chart_suggestion.get("reason", "") if chart_suggestion else "",
        "follow_ups": "|".join(follow_up_questions) if follow_up_questions else "",
        "created_at": datetime.datetime.now().isoformat(),
    }

    embedding = embedder.embed_single(query)

    coll.add(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[query],
        metadatas=[metadata],
    )

    logger.info("history_stored", doc_id=doc_id, query=query[:50])
    return doc_id


def find_similar(
    query: str,
    threshold: float = None,
    top_k: int = 5,
) -> Optional[Dict[str, Any]]:
    """搜索历史中最相似的问题

    使用 BGE 嵌入做余弦相似度匹配。只返回相似度 ≥ 阈值的最高分结果。

    Args:
        query: 用户当前问题
        threshold: 相似度阈值 (0-1)，默认从配置读取
        top_k: 检索候选数量

    Returns:
        如果命中: {"sql": str, "explanation": str, "score": float, "original_query": str}
        如果未命中: None
    """
    if threshold is None:
        threshold = get_settings().history_similarity_threshold

    coll = get_history_collection()
    embedder = get_embedder()

    # 检查是否有历史数据
    if coll.count() == 0:
        logger.info("history_empty")
        return None

    query_embedding = embedder.embed_single(query)

    results = coll.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, coll.count()),
        include=["documents", "metadatas", "distances"],
    )

    if not results["ids"] or not results["ids"][0]:
        logger.info("no_history_match", query=query[:50])
        return None

    # ChromaDB 返回 distance (越小越相似)，cosine distance 范围 [0, 2]
    # 转换为 similarity: similarity = 1 - distance/2
    best_distance = results["distances"][0][0]
    best_similarity = 1 - (best_distance / 2.0)
    best_meta = results["metadatas"][0][0]
    best_doc = results["documents"][0][0]

    logger.info(
        "history_search",
        query=query[:50],
        best_match=best_doc[:50],
        similarity=round(best_similarity, 4),
        threshold=threshold,
    )

    if best_similarity >= threshold:
        highlights_str = best_meta.get("highlights", "")
        follow_ups_str = best_meta.get("follow_ups", "")
        return {
            "sql": best_meta["sql"],
            "explanation": best_meta.get("explanation", ""),
            "score": best_similarity,
            "original_query": best_doc,
            "row_count": best_meta.get("row_count", 0),
            # 缓存完整结果 — 避免 LLM 重复生成
            "interpretation": best_meta.get("interpretation", ""),
            "highlights": [h for h in highlights_str.split("|") if h] if highlights_str else [],
            "chart_suggestion": {
                "type": best_meta.get("chart_type", ""),
                "reason": best_meta.get("chart_reason", ""),
            },
            "follow_up_questions": [q for q in follow_ups_str.split("|") if q] if follow_ups_str else [],
        }

    logger.info("history_below_threshold", score=round(best_similarity, 4), threshold=threshold)
    return None


def get_history_stats() -> Dict[str, Any]:
    """获取历史统计信息"""
    coll = get_history_collection()
    return {
        "total_entries": coll.count(),
        "collection_name": COLLECTION_NAME,
    }


def clear_history() -> None:
    """清空历史（开发调试用）"""
    try:
        client = get_chroma_client()
        client.delete_collection(COLLECTION_NAME)
        logger.info("history_cleared")
    except Exception:
        pass
