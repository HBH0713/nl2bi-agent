"""查询评测指标 — 记录每次查询的成功率、延迟、意图等"""
import time
from sqlalchemy import text
from src.db.connection import get_session
import structlog

logger = structlog.get_logger("metrics")

# 建表 SQL（幂等）
ENSURE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS query_metrics (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(12),
    session_id VARCHAR(30),
    query_text VARCHAR(500),
    intent VARCHAR(20),
    generated_sql TEXT,
    success BOOLEAN DEFAULT true,
    row_count INT DEFAULT 0,
    elapsed_ms FLOAT DEFAULT 0,
    cache_hit BOOLEAN DEFAULT false,
    correction_attempts INT DEFAULT 0,
    error_message VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT now()
);
"""

async def ensure_metrics_table():
    """确保指标表存在"""
    async for session in get_session():
        await session.execute(text(ENSURE_TABLE_SQL))
        await session.commit()


async def log_metrics(
    request_id: str, session_id: str, query: str,
    intent: str, sql: str, success: bool,
    row_count: int, elapsed_ms: float,
    cache_hit: bool = False, correction_attempts: int = 0,
    error: str = "",
):
    """记录一次查询指标"""
    try:
        await ensure_metrics_table()
        async for session in get_session():
            await session.execute(text("""
                INSERT INTO query_metrics
                (request_id, session_id, query_text, intent, generated_sql,
                 success, row_count, elapsed_ms, cache_hit, correction_attempts, error_message)
                VALUES (:rid, :sid, :q, :intent, :sql,
                        :success, :rows, :ms, :cache, :corr, :err)
            """), {
                "rid": request_id, "sid": session_id, "q": query[:500],
                "intent": intent, "sql": sql[:1000],
                "success": success, "rows": row_count, "ms": elapsed_ms,
                "cache": cache_hit, "corr": correction_attempts, "err": error[:500],
            })
            await session.commit()
            logger.info("metric_saved", rid=request_id, success=success, ms=elapsed_ms)
    except Exception as e:
        logger.warning("metric_save_failed", error=str(e))


async def get_metrics_summary():
    """获取评测指标摘要"""
    await ensure_metrics_table()
    async for session in get_session():
        total = await session.execute(text("SELECT COUNT(*) FROM query_metrics"))
        total_count = total.scalar() or 0

        success_rate = await session.execute(text(
            "SELECT FLOOR(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*)) FROM query_metrics"
        ))
        sr = success_rate.scalar() or 0

        avg_ms = await session.execute(text(
            "SELECT FLOOR(AVG(elapsed_ms)) FROM query_metrics"
        ))
        avg_time = avg_ms.scalar() or 0

        cache_rate = await session.execute(text(
            "SELECT FLOOR(100.0 * SUM(CASE WHEN cache_hit THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)) FROM query_metrics"
        ))
        cr = cache_rate.scalar() or 0

        intent_dist = await session.execute(text(
            "SELECT intent, COUNT(*) as cnt FROM query_metrics GROUP BY intent ORDER BY cnt DESC LIMIT 5"
        ))
        intents = [{"intent": r[0], "count": r[1]} for r in intent_dist.fetchall()]

        daily = await session.execute(text(
            "SELECT DATE(created_at) as d, COUNT(*) FROM query_metrics GROUP BY d ORDER BY d DESC LIMIT 7"
        ))
        daily_counts = [{"date": str(r[0]), "count": r[1]} for r in daily.fetchall()]

        recent = await session.execute(text(
            "SELECT request_id, query_text, intent, success, elapsed_ms, cache_hit "
            "FROM query_metrics ORDER BY created_at DESC LIMIT 20"
        ))
        recent_queries = [
            {"rid": r[0], "query": r[1][:60], "intent": r[2],
             "success": r[3], "ms": r[4], "cache": r[5]}
            for r in recent.fetchall()
        ]

        return {
            "total_queries": total_count,
            "success_rate": sr,
            "avg_response_ms": avg_time,
            "cache_hit_rate": cr,
            "intent_distribution": intents,
            "daily_counts": daily_counts,
            "recent_queries": recent_queries,
        }
