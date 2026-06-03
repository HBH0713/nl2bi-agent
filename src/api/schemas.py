from pydantic import BaseModel, Field
from typing import Optional, List, Any


class QueryRequest(BaseModel):
    query: str = Field(..., description="用自然语言描述的数据问题", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话标识，用于多轮追问，不传则自动创建新会话")


class QueryResponse(BaseModel):
    request_id: str = Field(..., description="请求唯一标识")
    session_id: str = Field(..., description="会话标识")
    intent: str = Field(..., description="意图分类结果：data_query / report_req / chitchat / ambiguous")
    generated_sql: str = Field(..., description="Agent 生成的 SQL 语句")
    sql_explanation: str = Field(..., description="SQL 的中文解释")
    sql_assumptions: List[str] = Field(default_factory=list, description="生成 SQL 时做出的假设")
    sql_risk_level: str = Field(..., description="SQL 风险等级：safe / warning / blocked")
    columns: List[str] = Field(default_factory=list, description="查询结果的列名列表")
    rows: List[List[Any]] = Field(default_factory=list, description="查询结果的数据行")
    row_count: int = Field(0, description="结果总行数")
    truncated: bool = Field(False, description="结果是否被截断")
    interpretation: str = Field("", description="AI 对数据的中文解读")
    highlights: List[str] = Field(default_factory=list, description="数据中的关键发现")
    chart_suggestion: dict = Field(default_factory=dict, description="推荐的可视化图表类型")
    follow_up_questions: List[str] = Field(default_factory=list, description="建议的追问方向")
    elapsed_ms: float = Field(0.0, description="查询总耗时（毫秒）")
    error: Optional[str] = Field(None, description="错误信息，成功时为 null")
    # 报表字段
    report_data: Optional[List[dict]] = Field(None, description="报表子查询结果列表")


class HealthResponse(BaseModel):
    status: str = Field(..., description="整体状态：healthy / degraded")
    version: str = Field(..., description="API 版本号")
    database: str = Field(..., description="PostgreSQL 连接状态：ok / unavailable")
    ollama: str = Field(..., description="Ollama 模型服务状态：ok / unavailable")
    chromadb: str = Field(..., description="ChromaDB 向量库状态：ok / unavailable")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="错误描述")
    detail: Optional[str] = Field(None, description="详细错误信息")
    request_id: Optional[str] = Field(None, description="请求标识")
