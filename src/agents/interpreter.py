import json
from src.agents.state import AgentState
from src.models.router import ModelRouter, ModelTask
from src.prompts.interpreter import build_interpreter_messages
from src.utils.json_parser import parse_llm_json
import structlog

logger = structlog.get_logger("agent.interpreter")


async def interpreter(state: AgentState, router: ModelRouter) -> dict:
    """结果解读节点 — 将查询结果转为自然语言"""
    query = state.get("user_query", "")
    sql = state.get("generated_sql", "")
    columns = state.get("query_columns", [])
    rows = state.get("query_rows", [])
    row_count = state.get("query_row_count", 0)
    truncated = state.get("query_truncated", False)
    error = state.get("query_error", "")

    if error:
        return {
            "interpretation": f"查询未能成功执行：{error}。请尝试修改查询条件后重试。",
            "highlights": [],
            "chart_suggestion": {"type": "none", "reason": ""},
            "follow_up_questions": ["能否换个角度重新提问？", "需要我帮您检查数据库中有哪些相关数据吗？"],
        }

    if row_count == 0:
        return {
            "interpretation": "查询执行成功但没有返回数据。这可能意味着：\n1. 查询条件过于严格，没有匹配的数据\n2. 该时间段内确实没有相关记录\n建议放宽时间范围或检查筛选条件。",
            "highlights": [],
            "chart_suggestion": {"type": "none", "reason": "无数据无需图表"},
            "follow_up_questions": ["试试扩大时间范围？", "当前数据库中有哪些表？"],
        }

    messages = build_interpreter_messages(query, sql, columns, rows, row_count, truncated)

    try:
        response = await router.chat_json(
            task=ModelTask.INTERPRET,
            messages=messages,
            temperature=0.3,
        )
        result = parse_llm_json(response.content)

        logger.info("Interpretation complete", row_count=row_count)

        return {
            "interpretation": result.get("summary", ""),
            "highlights": result.get("highlights", []),
            "chart_suggestion": result.get("chart_suggestion", {"type": "table", "reason": ""}),
            "follow_up_questions": result.get("follow_up_questions", []),
        }

    except Exception as e:
        logger.error("Interpretation failed", error=str(e))
        return {
            "interpretation": f"查询返回了 {row_count} 行数据。",
            "highlights": [],
            "chart_suggestion": {"type": "table", "reason": ""},
            "follow_up_questions": [],
        }
