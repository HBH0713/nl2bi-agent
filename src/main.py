from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.middleware import RequestLoggingMiddleware
from src.api.routes.query import router as query_router
from src.api.routes.health import router as health_router
from src.db.connection import init_db, close_db
from src.utils.logger import setup_logging
import structlog

logger = structlog.get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("NL2BI Agent 服务启动中")
    init_db()
    yield
    await close_db()
    logger.info("NL2BI Agent 服务已停止")


app = FastAPI(
    title="NL2BI Agent — 企业级自然语言数据分析平台",
    description="基于 LangGraph + FastAPI 的智能数据分析 Agent，支持自然语言转 SQL、自动报表生成。",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "数据查询", "description": "自然语言查询数据库，自动生成 SQL 并返回分析结果。"},
        {"name": "系统健康", "description": "检查各组件（数据库、Ollama、ChromaDB）运行状态。"},
    ],
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router)
app.include_router(health_router)


@app.get("/", tags=["系统信息"])
async def root():
    return {
        "服务": "NL2BI Agent API",
        "版本": "0.1.0",
        "文档": "/docs",
        "状态": "运行中",
    }
