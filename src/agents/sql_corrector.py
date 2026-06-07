"""
SQL 纠错循环 — 参照 WrenAI sql_diagnosis + sql_correction 模式

流程：验证失败 → 诊断错误原因 → 修正 SQL → 重新验证 → 最多 3 轮
"""
from src.agents.state import AgentState
from src.models.router import ModelRouter, ModelTask
from src.prompts.sql_gen import build_sql_gen_messages
from src.utils.json_parser import parse_llm_json
import structlog

logger = structlog.get_logger("agent.sql_corrector")

MAX_CORRECTION_RETRIES = 3

SQL_DIAGNOSIS_SYSTEM = """你是 ANSI SQL 调试专家。分析 SQL 错误的根因，给出简洁的诊断。

## 规则
1. 对照错误信息和数据库 Schema，找出根因
2. 重点关注：表名/列名拼写、JOIN 条件遗漏、语法错误、类型不匹配
3. 输出 JSON: {"reasoning": "用简洁中文描述根本原因和修复建议（50字以内）"}"""


async def _diagnose_error(
    sql: str,
    error_message: str,
    schema_context: str,
    router: ModelRouter,
) -> str:
    """用 Ollama 诊断 SQL 错误根因（参照 WrenAI sql_diagnosis）"""
    try:
        messages = [
            {"role": "system", "content": SQL_DIAGNOSIS_SYSTEM},
            {"role": "user", "content": f"""### 数据库 Schema ###\n{schema_context}\n\n### 原始 SQL ###\n{sql}\n\n### 错误信息 ###\n{error_message}\n\n请诊断错误原因。"""},
        ]
        response = await router.chat_json(task=ModelTask.SQL_VALIDATE, messages=messages, temperature=0.0)
        result = parse_llm_json(response.content)
        return result.get("reasoning", error_message[:100])
    except Exception as e:
        logger.warning("diagnosis_failed", error=str(e))
        return error_message[:200]  # fallback: 直接用原始错误


async def _correct_sql(
    sql: str,
    diagnosis: str,
    schema_context: str,
    query: str,
    router: ModelRouter,
) -> str:
    """用 DeepSeek 修正 SQL（参照 WrenAI sql_correction）"""
    try:
        system_prompt = """你是 ANSI SQL 专家。根据错误诊断修正 SQL。

## 修正规则
1. 只修正导致错误的部分，不要改其他逻辑
2. 确保表名/列名与 Schema 完全一致 — 如果错误提到表不存在，从 Schema 中找语义最接近的表替代
3. 如果无法精确修正，根据用户问题重新生成一个等效查询
4. 保持原有的查询意图不变
5. 输出 JSON: {"sql": "<修正后的SQL>", "explanation": "<修改了什么的简短说明>"}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""### 用户问题 ###
{query}

{('### 数据库 Schema ###' + chr(10) + schema_context) if schema_context else ''}

### 错误的 SQL ###
{sql}

### 错误信息 ###
{diagnosis}

请根据 Schema 修正 SQL。如果错误是因为表名/列名不存在，请重新生成一个使用正确表名的等效查询。"""},
        ]
        response = await router.chat_json(task=ModelTask.NL2SQL, messages=messages, temperature=0.1)
        result = parse_llm_json(response.content)
        corrected = result.get("sql", "")
        return corrected if corrected else sql
    except Exception as e:
        logger.error("correction_failed", error=str(e))
        return ""


async def sql_correction_loop(
    state: AgentState,
    router: ModelRouter,
) -> dict:
    """
    SQL 纠错循环 — 诊断 + 修正 + 重试

    在 sql_validator 判定失败后调用。
    """
    sql = state.get("generated_sql", "")
    query = state.get("user_query", "")
    schema_context = state.get("schema_context", "")
    error_count = state.get("error_count", 0)
    # executor 的错误在 query_error，validator 的在 sql_reject_reason
    qe = state.get("query_error", "")
    sr = state.get("sql_reject_reason", "")
    reject_reason = qe or sr or "未知错误"
    logger.info("correction_debug", qe=qe[:100], sr=sr[:100], reason=reject_reason[:100])

    # 检查是否已达到最大重试次数
    sql_correction_attempts = state.get("sql_correction_attempts", 0)
    if sql_correction_attempts >= MAX_CORRECTION_RETRIES:
        logger.info("correction_max_retries", attempts=sql_correction_attempts)
        return {
            "error_count": error_count,
            "recovery_path": "fallback",
            "sql_correction_attempts": sql_correction_attempts,
        }

    # Step 1: 诊断错误
    logger.info("correction_attempt", attempt=sql_correction_attempts + 1, error=reject_reason[:80])
    diagnosis = await _diagnose_error(sql, reject_reason, schema_context, router)

    # Step 2: 用诊断结果修正 SQL
    corrected_sql = await _correct_sql(sql, diagnosis, schema_context, query, router)

    if not corrected_sql or corrected_sql == sql:
        logger.warning("correction_no_change")
        return {
            "error_count": error_count + 1,
            "recovery_path": "fallback" if sql_correction_attempts + 1 >= MAX_CORRECTION_RETRIES else "rewrite",
            "sql_correction_attempts": sql_correction_attempts + 1,
            "sql_reject_reason": reject_reason,
        }

    logger.info("sql_corrected", original=sql[:100], corrected=corrected_sql[:100])

    return {
        "generated_sql": corrected_sql,
        "sql_explanation": f"（第{sql_correction_attempts + 1}次修正）{diagnosis[:80]}",
        "sql_assumptions": [f"自动修正: {diagnosis[:100]}"],
        "sql_valid": True,  # 标记为待验证
        "sql_risk_level": "safe",
        "sql_reject_reason": "",
        "recovery_path": "rewrite",
        "sql_correction_attempts": sql_correction_attempts + 1,
    }
