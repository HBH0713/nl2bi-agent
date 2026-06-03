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
import structlog

logger = structlog.get_logger("agent.graph")


# --- 路由函数 ---

def route_after_intent(state: AgentState) -> Literal["chitchat_handler", "schema_rag", "report_handler"]:
    intent = state.get("intent", "ambiguous")
    if intent == "chitchat":
        return "chitchat_handler"
    elif intent == "report_req":
        return "report_handler"
    else:
        return "schema_rag"


def route_after_validate(state: AgentState) -> Literal["executor", "reject_handler"]:
    if state.get("sql_valid", False):
        return "executor"
    return "reject_handler"


def route_after_execute(state: AgentState) -> Literal["interpreter", "reject_handler"]:
    if state.get("query_error", ""):
        return "reject_handler"
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


async def reject_handler(state: AgentState) -> dict:
    error_count = state.get("error_count", 0) + 1
    reason = state.get("sql_reject_reason", "未知错误")

    if error_count >= 2:
        return {
            "error_count": error_count,
            "recovery_path": "fallback",
            "interpretation": ("很抱歉，我多次尝试仍无法正确处理您的查询。"
                               f"最后一次遇到的问题：{reason}\n"
                               "建议：\n"
                               "1. 尝试用不同的方式描述您的需求\n"
                               "2. 明确指定您需要查询的指标和时间范围\n"
                               '3. 输入「帮助」查看我能处理的查询类型'),
            "highlights": [],
            "chart_suggestion": {"type": "none", "reason": ""},
            "follow_up_questions": ["有哪些表可以查询？", "帮我看看最近的数据"],
        }

    return {
        "error_count": error_count,
        "recovery_path": "rewrite",
        "interpretation": f"查询处理遇到问题：{reason}。正在尝试重新理解您的需求...",
        "highlights": [],
        "chart_suggestion": {"type": "none", "reason": ""},
        "follow_up_questions": [],
    }


# --- 构建 Graph ---

def build_agent_graph(router: ModelRouter) -> StateGraph:
    workflow = StateGraph(AgentState)

    # 节点 — 必须是 async 函数，LangGraph 会自动 await
    async def _intent_classifier(s): return await intent_classifier(s, router)
    async def _chitchat_handler(s): return await chitchat_handler(s, router)
    async def _report_planner(s): return await report_planner(s, router)
    async def _report_runner(s): return await report_runner(s, router)
    async def _schema_rag(s): return await schema_rag_retriever(s)
    async def _sql_generator(s): return await sql_generator(s, router)
    async def _sql_validator(s): return await sql_validator(s, router)
    async def _executor(s): return await sql_executor_node(s)
    async def _interpreter(s): return await interpreter(s, router)
    async def _reject_handler(s): return await reject_handler(s)

    workflow.add_node("intent_classifier", _intent_classifier)
    workflow.add_node("chitchat_handler", _chitchat_handler)
    workflow.add_node("report_planner", _report_planner)
    workflow.add_node("report_runner", _report_runner)
    workflow.add_node("schema_rag", _schema_rag)
    workflow.add_node("sql_generator", _sql_generator)
    workflow.add_node("sql_validator", _sql_validator)
    workflow.add_node("executor", _executor)
    workflow.add_node("interpreter", _interpreter)
    workflow.add_node("reject_handler", _reject_handler)

    # 边
    workflow.set_entry_point("intent_classifier")

    workflow.add_conditional_edges(
        "intent_classifier",
        route_after_intent,
        {
            "chitchat_handler": "chitchat_handler",
            "schema_rag": "schema_rag",
            "report_handler": "report_planner",
        },
    )

    workflow.add_edge("chitchat_handler", END)
    workflow.add_edge("report_planner", "report_runner")
    workflow.add_edge("report_runner", END)
    workflow.add_edge("schema_rag", "sql_generator")
    workflow.add_edge("sql_generator", "sql_validator")

    workflow.add_conditional_edges(
        "sql_validator",
        route_after_validate,
        {"executor": "executor", "reject_handler": "reject_handler"},
    )

    workflow.add_conditional_edges(
        "executor",
        route_after_execute,
        {"interpreter": "interpreter", "reject_handler": "reject_handler"},
    )

    workflow.add_edge("interpreter", END)
    workflow.add_edge("reject_handler", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
