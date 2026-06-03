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
    logger.info("Starting NL2BI Agent API server")
    init_db()
    yield
    await close_db()
    logger.info("NL2BI Agent API server stopped")


app = FastAPI(
    title="NL2BI Agent API",
    description="Natural Language to Business Intelligence Agent",
    version="0.1.0",
    lifespan=lifespan,
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


@app.get("/")
async def root():
    return {"message": "NL2BI Agent API is running", "docs": "/docs"}
