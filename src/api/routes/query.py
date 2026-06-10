import time
import uuid
import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from src.api.schemas import QueryRequest, QueryResponse
from src.agents.graph import build_agent_graph
from src.models.router import ModelRouter
from src.config import get_settings
from src.models.ollama import OllamaClient
from src.models.openai_compat import OpenAICompatClient
from src.db.connection import init_db
from src.utils.data_masker import is_sensitive_column, mask_dataframe
from src.utils.metrics import log_metrics, get_metrics_summary
import structlog
import pandas as pd

NODE_LABELS = {
    "intent_classifier": "🎯 分析意图",
    "history_matcher": "🧠 查找缓存",
    "schema_rag": "🔍 检索表结构",
    "sql_generator": "📝 AI 生成 SQL",
    "sql_validator": "✅ 校验 SQL",
    "sql_corrector": "🔧 自动修正 SQL",
    "executor": "⚡ 执行查询",
    "interpreter": "💡 AI 解读结果",
    "store_history": "💾 保存记录",
    "reject_handler": "⚠️ 处理错误",
    "chitchat_handler": "💬",
    "report_planner": "🤖 多Agent规划 — 拆解复杂问题",
    "report_runner": "⚡ 多Agent并行 — 同时执行子查询",
}

logger = structlog.get_logger("api.query")

router = APIRouter(prefix="/api", tags=["数据查询"])

_agent_graph = None
_router: ModelRouter = None


def get_agent():
    global _agent_graph, _router
    if _agent_graph is None:
        settings = get_settings()
        init_db()

        ollama = OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
        )
        api = OpenAICompatClient(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            base_url=settings.deepseek_base_url,
        )
        _router = ModelRouter(ollama=ollama, api=api)
        _agent_graph = build_agent_graph(_router)

    return _agent_graph


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="自然语言查询",
    description="输入中文问题，自动完成意图识别 → 表结构检索 → SQL 生成 → 安全校验 → 执行 → 结果解读的完整链路。",
)
async def query_data(req: QueryRequest):
    start = time.time()
    request_id = str(uuid.uuid4())[:8]
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"

    graph = get_agent()
    config = {"configurable": {"thread_id": session_id}}

    try:
        initial_state = {"user_query": req.query, "error_count": 0}
        if req.previous_sql:
            initial_state["generated_sql"] = req.previous_sql
            logger.info("multi_turn_context", prev=req.previous_sql[:80])

        result = await graph.ainvoke(initial_state, config=config)

        # 数据脱敏
        columns = result.get("query_columns", [])
        rows = result.get("query_rows", [])
        sensitive_cols = [c for c in columns if is_sensitive_column(c)]
        if sensitive_cols and rows:
            import pandas as pd
            df = pd.DataFrame(rows, columns=columns)
            masked = mask_dataframe(df, sensitive_cols)
            rows = masked["rows"]
            logger.info("Data masked", columns=sensitive_cols, masked_count=len(masked.get("masked", [])))

        elapsed = (time.time() - start) * 1000

        response = QueryResponse(
            request_id=request_id,
            session_id=session_id,
            intent=result.get("intent", ""),
            generated_sql=result.get("generated_sql", ""),
            sql_explanation=result.get("sql_explanation", ""),
            sql_assumptions=result.get("sql_assumptions", []),
            sql_risk_level=result.get("sql_risk_level", "safe"),
            columns=columns,
            rows=rows,
            row_count=result.get("query_row_count", 0),
            truncated=result.get("query_truncated", False),
            interpretation=result.get("interpretation", ""),
            highlights=result.get("highlights", []),
            chart_suggestion=result.get("chart_suggestion", {}),
            follow_up_questions=result.get("follow_up_questions", []),
            elapsed_ms=elapsed,
            error=result.get("query_error"),
            report_data=result.get("report_data"),
        )

        logger.info(
            "Query completed",
            request_id=request_id,
            session_id=session_id,
            intent=response.intent,
            row_count=response.row_count,
            elapsed_ms=elapsed,
        )

        # 记录评测指标
        import asyncio as _asyncio
        _asyncio.create_task(log_metrics(
            request_id=request_id, session_id=session_id,
            query=req.query, intent=response.intent,
            sql=response.generated_sql,
            success=not bool(response.error),
            row_count=response.row_count,
            elapsed_ms=elapsed,
            cache_hit=result.get("history_matched", False),
            correction_attempts=result.get("sql_correction_attempts", 0),
            error=response.error or "",
        ))

        return response

    except Exception as e:
        logger.error("Query failed", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/stream", summary="流式自然语言查询（SSE）")
async def query_data_stream(req: QueryRequest):
    """SSE 流式返回 Agent 每个节点的执行状态，前端实时显示进度"""
    request_id = str(uuid.uuid4())[:8]
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    graph = get_agent()
    config = {"configurable": {"thread_id": session_id}}

    async def event_stream():
        initial_state = {"user_query": req.query, "error_count": 0}
        if req.previous_sql:
            initial_state["generated_sql"] = req.previous_sql

        last_node = ""
        try:
            async for event in graph.astream(initial_state, config=config):
                for node_name, node_output in event.items():
                    if node_name in NODE_LABELS:
                        label = NODE_LABELS[node_name]
                        # 为关键节点附加详情
                        detail = ""
                        if node_name == "history_matcher" and node_output.get("history_matched"):
                            detail = f" (命中缓存, 相似度 {node_output.get('history_score', 0):.0%})"
                        elif node_name == "sql_generator":
                            sql = node_output.get("generated_sql", "")
                            if sql:
                                detail = f"\n```sql\n{sql[:200]}\n```"
                        elif node_name == "executor":
                            rows = node_output.get("query_row_count", 0)
                            err = node_output.get("query_error", "")
                            detail = f" ({rows} 行)" if rows else f" (失败: {err[:60]})" if err else ""
                        elif node_name == "reject_handler":
                            path = node_output.get("recovery_path", "")
                            detail = f" ({'自动修正中...' if path == 'correct' else '已放弃'})"

                        yield f"data: {json.dumps({'node': node_name, 'label': label, 'detail': detail}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'node': 'done', 'label': '✅ 完成'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'node': 'error', 'label': f'❌ {str(e)[:100]}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/metrics", summary="查询评测指标")
async def get_metrics():
    """返回查询评测数据：成功率、延迟分布、意图分布、近期查询"""
    try:
        return await get_metrics_summary()
    except Exception as e:
        return {"error": str(e), "total_queries": 0}
