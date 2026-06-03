from fastapi import APIRouter
from src.api.schemas import HealthResponse
from src.config import get_settings
from src.db.chroma_client import get_chroma_client
import structlog

logger = structlog.get_logger("api.health")
router = APIRouter(tags=["系统健康"])


@router.get(
    "/api/health",
    response_model=HealthResponse,
    summary="系统健康检查",
    description="检查 PostgreSQL 数据库、Ollama 本地模型、ChromaDB 向量库的连接状态。",
)
async def health_check():
    settings = get_settings()

    chroma_status = "ok"
    try:
        get_chroma_client()
    except Exception:
        chroma_status = "unavailable"

    ollama_status = "unknown"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            ollama_status = "ok" if resp.status_code == 200 else "error"
    except Exception:
        ollama_status = "unavailable"

    db_status = "unknown"
    try:
        from sqlalchemy import text
        from src.db.connection import get_session
        async for session in get_session():
            await session.execute(text("SELECT 1"))
            db_status = "ok"
            break
    except Exception:
        db_status = "unavailable"

    all_ok = all(s == "ok" for s in [db_status, ollama_status, chroma_status])

    return HealthResponse(
        status="healthy" if all_ok else "degraded",
        version="0.1.0",
        database=db_status,
        ollama=ollama_status,
        chromadb=chroma_status,
    )
