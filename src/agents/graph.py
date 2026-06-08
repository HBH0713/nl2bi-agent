from typing import Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.agents.state import AgentState
from src.agents.intent import intent_classifier
from src.agents.schema_rag import schema_rag_retriever
from src.agents.sql_generator import sql_generator
from src.agents.sql_validator import sql_validator
from src.agents.interpreter import interpreter
from src.agents.report_planner import report_planner
from src.agents.report_runner import report_runner
from src.db.executor import execute_query
from src.db.connection import get_session
from src.models.router import ModelRouter
from src.rag.query_history import find_similar, add_to_history
from src.agents.sql_corrector import sql_correction_loop, MAX_CORRECTION_RETRIES
from src.config import get_settings
import structlog

logger = structlog.get_logger("agent.graph")


# --- 路由函数 ---

def route_after_intent(state: AgentState) -> Literal["chitchat_handler", "history_matcher", "report_handler"]:
    intent = state.get("intent", "ambiguous")
    if intent == "chitchat":
        return "chitchat_handler"
    elif intent == "report_req":
        return "report_handler"
    else:
        return "history_matcher"


def route_after_history(state: AgentState) -> Literal["executor", "schema_rag"]:
    """命中历史缓存则跳过 SQL 生成直接执行"""
    if state.get("history_matched", False):
        return "executor"
    return "schema_rag"


def route_after_validate(state: AgentState) -> Literal["executor", "reject_handler"]:
    if state.get("sql_valid", False):
        return "executor"
    return "reject_handler"


def route_after_execute(state: AgentState) -> Literal["interpreter", "store_history", "reject_handler"]:
    if state.get("query_error", ""):
        logger.info("route_execute: reject_handler", error=state.get("query_error", "")[:80])
        return "reject_handler"
    # 历史命中时已有完整解释，跳过 interpreter
    if state.get("history_matched", False):
        logger.info("route_execute: store_history (history_hit)")
        return "store_history"
    logger.info("route_execute: interpreter")
    return "interpreter"


# --- 处理器节点 ---

async def chitchat_handler(state: AgentState, router: ModelRouter) -> dict:
    return {
        "interpretation": ("您好！我是 BI 数据分析助手。您可以问我任何关于业务数据的问题，比如：\n"
                           "- 「上个月各区域的销售额是多少？」\n"
                           "- 「哪个产品卖得最好？」\n"
                           "- 「本周的订单量趋势如何？」\n"
                           "请问您想了解什么数据？"),
        "highlights": [],
        "chart_suggestion": {"type": "none", "reason": ""},
        "follow_up_questions": [],
    }


async def sql_executor_node(state: AgentState) -> dict:
    sql = state.get("generated_sql", "")
    if not sql:
        return {
            "query_error": "没有可执行的 SQL",
            "query_columns": [],
            "query_rows": [],
            "query_row_count": 0,
            "query_elapsed_ms": 0,
            "query_truncated": False,
        }

    async for session in get_session():
        result = await execute_query(sql, session)
        return {
            "query_columns": result.columns,
            "query_rows": result.rows,
            "query_row_count": result.row_count,
            "query_elapsed_ms": result.elapsed_ms,
            "query_truncated": result.truncated,
            "query_error": result.error or "",
        }


async def history_matcher_node(state: AgentState) -> dict:
    """历史问题匹配节点 — 在进入 SQL 生成前先查缓存"""
    settings = get_settings()

    if not settings.history_enabled:
        return {
            "history_matched": False,
            "history_score": 0.0,
            "history_original_query": "",
        }

    query = state.get("user_query", "")
    if not query:
        return {
            "history_matched": False,
            "history_score": 0.0,
            "history_original_query": "",
        }

    # 多轮对话中跳过缓存——追问需要基于上轮结果重新生成SQL
    messages = state.get("messages", [])
    if len(messages) >= 2:
        # 有对话历史说明是多轮对话，不走缓存
        return {
            "history_matched": False,
            "history_score": 0.0,
            "history_original_query": "",
        }

    result = find_similar(query, threshold=settings.history_similarity_threshold)

    if result:
        logger.info("history_hit", query=query[:50], score=round(result["score"], 4))
        return {
            "history_matched": True,
            "history_score": result["score"],
            "history_original_query": result["original_query"],
            "generated_sql": result["sql"],
            "sql_explanation": result.get("explanation", "（复用历史缓存 SQL）"),
            "sql_assumptions": ["查询历史匹配命中，跳过 SQL 生成和结果解释"],
            "sql_valid": True,
            "sql_risk_level": "safe",
            # 完整缓存 — 跳过 interpreter
            "interpretation": result.get("interpretation", ""),
            "highlights": result.get("highlights", []),
            "chart_suggestion": result.get("chart_suggestion", {}),
            "follow_up_questions": result.get("follow_up_questions", []),
        }
    else:
        return {
            "history_matched": False,
            "history_score": 0.0,
            "history_original_query": "",
        }


async def store_history_node(state: AgentState) -> dict:
    """查询成功后存储历史 — 在 interpreter 之后执行"""
    query = state.get("user_query", "")
    sql = state.get("generated_sql", "")
    query_error = state.get("query_error", "")

    # 只在成功执行时存储
    if not query or not sql or query_error:
        return {}

    if state.get("history_matched", False):
        # 本身就是从缓存来的，不需要重复存储
        return {}

    try:
        add_to_history(
            query=query,
            sql=sql,
            explanation=state.get("sql_explanation", ""),
            row_count=state.get("query_row_count", 0),
            interpretation=state.get("interpretation", ""),
            highlights=state.get("highlights", []),
            chart_suggestion=state.get("chart_suggestion", {}),
            follow_up_questions=state.get("follow_up_questions", []),
        )
        logger.info("history_stored_after_query", query=query[:50])
    except Exception as e:
        logger.warning("history_store_failed", error=str(e))

    return {}


async def reject_handler(state: AgentState) -> dict:
    """错误处理 — 尝试纠错，超出上限则降级"""
    error_count = state.get("error_count", 0) + 1
    # executor 和 validator 的错误可能在不同字段
    reason = (
        state.get("query_error", "") or
        state.get("sql_reject_reason", "") or
        "未知错误"
    )
    correction_attempts = state.get("sql_correction_attempts", 0)
    logger.info("reject_handler", reason_preview=reason[:100], attempts=correction_attempts)

    # SQL 修正未达上限 → 进入纠错循环
    if correction_attempts < MAX_CORRECTION_RETRIES:
        logger.info("reject_routing_to_corrector", attempts=correction_attempts, reason=reason[:80])
        return {
            "error_count": error_count,
            "recovery_path": "correct",
            "interpretation": f"SQL 校验未通过：{reason}。正在尝试自动修正...",
            "highlights": [],
            "chart_suggestion": {"type": "none", "reason": ""},
            "follow_up_questions": [],
        }

    # 已修正多次仍失败 → 降级
    logger.info("reject_max_retries_exhausted", attempts=correction_attempts)
    return {
        "error_count": error_count,
        "recovery_path": "fallback",
        "interpretation": (f"很抱歉，经过 {MAX_CORRECTION_RETRIES} 次自动修正仍无法处理您的查询。"
                           f"最后遇到的问题：{reason}\n\n"
                           "建议：\n"
                           "1. 尝试用不同的方式描述您的需求\n"
                           "2. 明确指定查询的指标和时间范围\n"
                           '3. 输入「帮助」查看示例'),
        "highlights": [],
        "chart_suggestion": {"type": "none", "reason": ""},
        "follow_up_questions": ["有哪些表可以查询？", "帮我看看最近的数据"],
    }


# --- 构建 Graph ---

def build_agent_graph(router: ModelRouter) -> StateGraph:
    workflow = StateGraph(AgentState)

    # 节点 — 必须是 async 函数，LangGraph 会自动 await
    async def _intent_classifier(s): return await intent_classifier(s, router)
    async def _chitchat_handler(s): return await chitchat_handler(s, router)
    async def _report_planner(s): return await report_planner(s, router)
    async def _report_runner(s): return await report_runner(s, router)
    async def _history_matcher(s): return await history_matcher_node(s)
    async def _schema_rag(s): return await schema_rag_retriever(s)
    async def _sql_generator(s): return await sql_generator(s, router)
    async def _sql_validator(s): return await sql_validator(s, router)
    async def _sql_corrector(s): return await sql_correction_loop(s, router)
    async def _executor(s): return await sql_executor_node(s)
    async def _interpreter(s): return await interpreter(s, router)
    async def _store_history(s): return await store_history_node(s)
    async def _reject_handler(s): return await reject_handler(s)

    workflow.add_node("intent_classifier", _intent_classifier)
    workflow.add_node("chitchat_handler", _chitchat_handler)
    workflow.add_node("report_planner", _report_planner)
    workflow.add_node("report_runner", _report_runner)
    workflow.add_node("history_matcher", _history_matcher)
    workflow.add_node("schema_rag", _schema_rag)
    workflow.add_node("sql_generator", _sql_generator)
    workflow.add_node("sql_validator", _sql_validator)
    workflow.add_node("sql_corrector", _sql_corrector)
    workflow.add_node("executor", _executor)
    workflow.add_node("interpreter", _interpreter)
    workflow.add_node("store_history", _store_history)
    workflow.add_node("reject_handler", _reject_handler)

    # 边
    workflow.set_entry_point("intent_classifier")

    workflow.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "chitchat_handler": "chitchat_handler",
            "history_matcher": "history_matcher",
            "report_handler": "report_planner",
        },
    )

    workflow.add_edge("chitchat_handler", END)
    workflow.add_edge("report_planner", "report_runner")
    workflow.add_edge("report_runner", END)

    # 历史匹配 → 命中则跳过 SQL 生成直接执行，否则走原有流程
    workflow.add_conditional_edges(
        "history_matcher",
        route_after_history,
        {"executor": "executor", "schema_rag": "schema_rag"},
    )

    workflow.add_edge("schema_rag", "sql_generator")
    workflow.add_edge("sql_generator", "sql_validator")

    workflow.add_conditional_edges(
        "sql_validator",
        route_after_validate,
        {"executor": "executor", "reject_handler": "reject_handler"},
    )

    # 纠错循环：reject → sql_corrector → sql_validator (最多3轮)
    workflow.add_conditional_edges(
        "reject_handler",
        lambda s: "sql_corrector" if s.get("recovery_path") == "correct" else END,
        {"sql_corrector": "sql_corrector", END: END},
    )
    workflow.add_conditional_edges(
        "sql_corrector",
        lambda s: "sql_validator" if s.get("recovery_path") == "rewrite" else END,
        {"sql_validator": "sql_validator", END: END},
    )

    workflow.add_conditional_edges(
        "executor",
        route_after_execute,
        {
            "interpreter": "interpreter",
            "store_history": "store_history",
            "reject_handler": "reject_handler",
        },
    )

    # 解释后存储历史（非缓存路径）
    workflow.add_edge("interpreter", "store_history")
    workflow.add_edge("store_history", END)
    # reject_handler → sql_corrector 或 END 已在条件边中定义

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
