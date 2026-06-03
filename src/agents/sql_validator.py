import json
from src.agents.state import AgentState
from src.utils.sql_parser import validate_sql
from src.utils.json_parser import parse_llm_json
from src.models.router import ModelRouter, ModelTask
import structlog

logger = structlog.get_logger("agent.sql_validator")


async def sql_validator(state: AgentState, router: ModelRouter) -> dict:
    """SQL 校验节点 — L1 语法 + L2 安全规则 + L3 语义（可选）"""
    sql = state.get("generated_sql", "")

    if not sql:
        return {
            "sql_valid": False,
            "sql_risk_level": "blocked",
            "sql_reject_reason": "未生成有效的 SQL 语句",
        }

    # L1 + L2: 语法解析 + 安全规则
    validation = validate_sql(sql)

    if not validation.is_valid:
        logger.warning("SQL validation failed", reason=validation.error_message)
        return {
            "sql_valid": False,
            "sql_risk_level": validation.risk_level,
            "sql_reject_reason": validation.error_message or "SQL 校验未通过",
        }

    # L3: 语义校验（可选，使用 Ollama）
    if validation.risk_level == "warning":
        semantic_check = await _semantic_check(sql, state.get("user_query", ""), router)
        if semantic_check.get("has_issue"):
            validation.warnings.append(semantic_check["issue"])

    return {
        "sql_valid": True,
        "sql_risk_level": validation.risk_level,
        "sql_reject_reason": "",
    }


async def _semantic_check(sql: str, query: str, router: ModelRouter) -> dict:
    """L3 语义校验：用 Ollama 检查 SQL 逻辑是否合理"""
    try:
        messages = [
            {"role": "system", "content": "你是 SQL 审查专家。检查 SQL 是否与用户问题匹配。返回 JSON: {\"has_issue\": bool, \"issue\": \"问题描述(无问题则为空)\"}"},
            {"role": "user", "content": f"用户问题: {query}\nSQL: {sql}\n请检查逻辑是否一致，重点关注：表选择是否正确、WHERE 条件是否遗漏、聚合逻辑是否合理。"},
        ]
        response = await router.chat_json(task=ModelTask.SQL_VALIDATE, messages=messages, temperature=0.0)
        return parse_llm_json(response.content)
    except Exception:
        return {"has_issue": False, "issue": ""}
