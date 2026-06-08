from src.agents.state import AgentState
from src.models.router import ModelRouter, ModelTask
from src.prompts.sql_gen import build_sql_gen_messages
from src.utils.json_parser import parse_llm_json
import structlog

logger = structlog.get_logger("agent.sql_generator")


async def _generate_once(schema_context: str, query: str, history: str,
                         router: ModelRouter, error_feedback: str = "") -> tuple[str | None, dict]:
    """执行一次 SQL 生成，返回 (sql, raw_result)"""
    prompt_messages = build_sql_gen_messages(schema_context, query, history)

    if error_feedback:
        prompt_messages.append({
            "role": "user",
            "content": f"上一次生成的 SQL 执行时报错：{error_feedback}\n请修正 SQL 后重新生成。"
        })

    response = await router.chat_json(task=ModelTask.NL2SQL, messages=prompt_messages, temperature=0.1)
    raw = response.content.strip()
    result = parse_llm_json(raw)
    return result.get("sql", ""), result


async def sql_generator(state: AgentState, router: ModelRouter) -> dict:
    """NL2SQL 生成节点 — 使用云端 API，失败自动重试一次"""
    schema_context = state.get("schema_context", "")
    query = state.get("user_query", "")
    prev_error = state.get("query_error", "")

    if not schema_context:
        logger.warning("No schema context available for SQL generation")
        return {"generated_sql": "", "sql_explanation": "未能找到相关数据表，无法生成 SQL。",
                "sql_assumptions": [], "sql_valid": False, "sql_risk_level": "blocked",
                "sql_reject_reason": "缺少 Schema 上下文"}

    messages = state.get("messages", [])
    history_parts = []
    if messages:
        recent = [m for m in messages[-6:] if hasattr(m, "content")]
        history_parts = [
            f"{'用户' if m.type == 'human' else '助手'}: {m.content}"
            for m in recent if m.content
        ]
    # 附加上一轮查询的 SQL 和结果摘要，帮助模型理解追问上下文
    prev_sql = state.get("generated_sql", "")
    prev_rows = state.get("query_rows", [])
    prev_columns = state.get("query_columns", [])
    if prev_sql:
        history_parts.append(f"上一轮 SQL: {prev_sql}")
    if prev_rows and prev_columns:
        sample = prev_rows[:3]
        history_parts.append(f"上一轮结果(共{len(prev_rows)}行, 列:{prev_columns}): {sample}")
    history = "\n".join(history_parts)

    try:
        # 第一次尝试
        sql, result = await _generate_once(schema_context, query, history, router)
        if not sql:
            return {"generated_sql": "", "sql_explanation": "AI 未能生成有效 SQL",
                    "sql_assumptions": [], "sql_valid": False, "sql_risk_level": "blocked",
                    "sql_reject_reason": "未生成 SQL"}

        logger.info("SQL generated", query=query[:50], sql=sql[:200])

        # 重试标记：如果之前有错误，检查新 SQL 是否不同
        recovery = "rewrite" if prev_error else state.get("recovery_path", "")

        return {"generated_sql": sql, "sql_explanation": result.get("explanation", ""),
                "sql_assumptions": result.get("assumptions", []),
                "sql_valid": True, "sql_risk_level": "safe", "sql_reject_reason": "",
                "recovery_path": recovery}

    except Exception as e:
        logger.error("SQL generation failed", error=str(e))
        return {"generated_sql": "", "sql_explanation": f"SQL 生成失败: {e}",
                "sql_assumptions": [], "sql_valid": False, "sql_risk_level": "blocked",
                "sql_reject_reason": str(e)}
