import time
import uuid
from fastapi import APIRouter, HTTPException
from src.api.schemas import QueryRequest, QueryResponse
from src.agents.graph import build_agent_graph
from src.models.router import ModelRouter
from src.config import get_settings
from src.models.ollama import OllamaClient
from src.models.openai_compat import OpenAICompatClient
from src.db.connection import init_db
from src.utils.data_masker import is_sensitive_column, mask_dataframe
import structlog
import pandas as pd

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
        result = await graph.ainvoke(
            {"user_query": req.query, "error_count": 0},
            config=config,
        )

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

        return response

    except Exception as e:
        logger.error("Query failed", request_id=request_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
