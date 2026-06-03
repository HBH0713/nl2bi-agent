import json
from src.agents.state import AgentState
from src.models.router import ModelRouter, ModelTask
from src.prompts.sql_gen import build_sql_gen_messages
from src.utils.json_parser import parse_llm_json
import structlog

logger = structlog.get_logger("agent.sql_generator")


async def sql_generator(state: AgentState, router: ModelRouter) -> dict:
    """NL2SQL 生成节点 — 使用云端 API（精度优先）"""
    schema_context = state.get("schema_context", "")
    query = state.get("user_query", "")

    if not schema_context:
        logger.warning("No schema context available for SQL generation")
        return {
            "generated_sql": "",
            "sql_explanation": "未能找到相关数据表，无法生成 SQL。",
            "sql_assumptions": [],
        }

    messages = state.get("messages", [])
    history = ""
    if messages:
        recent = [m for m in messages[-6:] if hasattr(m, "content")]
        history = "\n".join(
            f"{'用户' if m.type == 'human' else '助手'}: {m.content}"
            for m in recent if m.content
        )

    prompt_messages = build_sql_gen_messages(schema_context, query, history)

    try:
        response = await router.chat_json(
            task=ModelTask.NL2SQL,
            messages=prompt_messages,
            temperature=0.1,
        )
        raw = response.content.strip()
        result = parse_llm_json(raw)

        sql = result.get("sql", "")

        logger.info(
            "SQL generated",
            query=query[:50],
            sql=sql[:200],
            tokens=response.tokens_used,
            cost=response.cost_usd,
        )

        return {
            "generated_sql": sql,
            "sql_explanation": result.get("explanation", ""),
            "sql_assumptions": result.get("assumptions", []),
            "sql_valid": True,
            "sql_risk_level": "safe",
            "sql_reject_reason": "",
        }

    except Exception as e:
        logger.error("SQL generation failed", error=str(e))
        return {
            "generated_sql": "",
            "sql_explanation": f"SQL 生成失败: {e}",
            "sql_assumptions": [],
            "sql_valid": False,
            "sql_risk_level": "blocked",
            "sql_reject_reason": str(e),
        }
