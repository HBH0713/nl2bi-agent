"""报告运行器 — 并发执行所有子查询，汇总生成最终报表"""
import asyncio
import time
from src.agents.state import AgentState
from src.models.router import ModelRouter, ModelTask
from src.rag.retriever import build_schema_context
from src.prompts.sql_gen import build_sql_gen_messages
from src.utils.json_parser import parse_llm_json
from src.db.executor import execute_query
from src.db.connection import get_session
import structlog

logger = structlog.get_logger("agent.report_runner")


async def _run_single_query(question: str, router: ModelRouter) -> dict:
    """执行单个子查询，返回结果"""
    import json as _json

    # 1. Schema RAG
    schema_context = build_schema_context(question, top_tables=5)
    if not schema_context:
        return {"question": question, "error": "无匹配数据表", "rows": [], "columns": []}

    # 2. NL2SQL
    prompt_messages = build_sql_gen_messages(schema_context, question)
    try:
        response = await router.chat_json(task=ModelTask.NL2SQL, messages=prompt_messages, temperature=0.1)
        result = parse_llm_json(response.content)
        sql = result.get("sql", "")
    except Exception as e:
        return {"question": question, "error": f"SQL 生成失败: {e}", "rows": [], "columns": []}

    if not sql:
        return {"question": question, "error": "未生成 SQL", "rows": [], "columns": []}

    # 3. Execute
    async for session in get_session():
        exec_result = await execute_query(sql, session)
        return {
            "question": question,
            "sql": sql,
            "columns": exec_result.columns,
            "rows": exec_result.rows[:20],  # 每个子查询最多 20 行
            "row_count": exec_result.row_count,
            "error": exec_result.error or "",
            "elapsed_ms": exec_result.elapsed_ms,
        }


async def report_runner(state: AgentState, router: ModelRouter) -> dict:
    """并发执行所有子查询，生成汇总报表"""
    sub_queries = state.get("report_sub_queries", [])
    if not sub_queries:
        return {}

    start = time.time()
    questions = [sq["question"] for sq in sub_queries]

    # 并发执行所有子查询
    tasks = [_run_single_query(q, router) for q in questions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理异常
    processed = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            processed.append({"question": questions[i], "error": str(r), "rows": [], "columns": []})
        else:
            processed.append(r)

    total_elapsed = (time.time() - start) * 1000

    # 生成报告摘要
    summary_lines = [f"## {state.get('report_title', '数据报表')}"]
    summary_lines.append(f"时间范围：{state.get('report_date_range', '近7天')}\n")

    total_rows = 0
    for r in processed:
        q = r["question"]
        err = r.get("error", "")
        n = r.get("row_count", 0)
        total_rows += n
        if err:
            summary_lines.append(f"- **{q}**：查询异常（{err}）")
        elif n == 0:
            summary_lines.append(f"- **{q}**：无数据")
        else:
            first_row = r.get("rows", [[0]])[0]
            col_names = r.get("columns", [])
            brief = ""
            if len(first_row) >= 2 and len(col_names) >= 2:
                brief = f" {col_names[0]}={first_row[0]}, {col_names[1]}={first_row[1]}"
            summary_lines.append(f"- **{q}**：{n} 条数据{brief}")

    summary_lines.append(f"\n> 共执行 {len(processed)} 个指标，总耗时 {total_elapsed:.0f}ms")

    logger.info("Report completed", queries_count=len(processed), total_rows=total_rows, elapsed_ms=total_elapsed)

    return {
        "interpretation": "\n".join(summary_lines),
        "report_data": processed,
        "report_elapsed_ms": total_elapsed,
        "query_elapsed_ms": total_elapsed,
        "query_row_count": total_rows,
    }
