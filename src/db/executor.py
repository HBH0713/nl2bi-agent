import time
from dataclasses import dataclass
from typing import Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import get_settings
import structlog

logger = structlog.get_logger("sql_executor")


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    elapsed_ms: float
    truncated: bool = False
    error: Optional[str] = None


async def execute_query(
    sql: str,
    session: AsyncSession,
    timeout_s: Optional[int] = None,
    max_rows: Optional[int] = None,
) -> QueryResult:
    """在沙箱中执行 SQL 查询"""
    settings = get_settings()
    timeout_s = timeout_s or settings.max_query_timeout_s
    max_rows = max_rows or settings.max_return_rows

    start = time.time()

    try:
        await session.execute(text(f"SET LOCAL statement_timeout = '{timeout_s}s'"))
        await session.execute(text(f"SET LOCAL max_rows = {max_rows}"))
        if settings.sql_read_only:
            await session.execute(text("SET LOCAL default_transaction_read_only = on"))

        result = await session.execute(text(sql))
        rows = result.fetchall()
        columns = list(result.keys())
        elapsed = (time.time() - start) * 1000

        row_count = len(rows)
        truncated = row_count >= max_rows

        if elapsed > 5000:
            logger.warning("Slow query detected", sql=sql[:300], elapsed_ms=round(elapsed), row_count=row_count)

        logger.info("Query executed", elapsed_ms=round(elapsed), row_count=row_count, truncated=truncated)

        return QueryResult(
            columns=columns,
            rows=[list(r) for r in rows],
            row_count=row_count,
            elapsed_ms=elapsed,
            truncated=truncated,
        )

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        error_msg = str(e)

        if "statement_timeout" in error_msg.lower() or "canceling statement" in error_msg.lower():
            error_msg = f"查询超时（>{timeout_s}秒）。请尝试缩小查询范围。"
        elif "max_rows" in error_msg.lower():
            error_msg = f"返回行数超过限制（{max_rows}行）。请添加更多过滤条件。"

        logger.error("Query failed", sql=sql[:300], error=error_msg, elapsed_ms=round(elapsed))

        return QueryResult(
            columns=[],
            rows=[],
            row_count=0,
            elapsed_ms=elapsed,
            error=error_msg,
        )
