from pydantic import BaseModel, Field
from typing import Optional, List, Any


class QueryRequest(BaseModel):
    query: str = Field(..., description="用户自然语言查询", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话 ID，用于多轮对话")


class QueryResponse(BaseModel):
    request_id: str
    session_id: str
    intent: str
    generated_sql: str
    sql_explanation: str
    sql_assumptions: List[str] = []
    sql_risk_level: str
    columns: List[str] = []
    rows: List[List[Any]] = []
    row_count: int = 0
    truncated: bool = False
    interpretation: str
    highlights: List[str] = []
    chart_suggestion: dict = {}
    follow_up_questions: List[str] = []
    elapsed_ms: float = 0.0
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    ollama: str
    chromadb: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
