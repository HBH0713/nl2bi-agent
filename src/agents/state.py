from typing import TypedDict, List, Dict, Annotated, Any
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    user_query: str
    intent: str                              # chitchat | data_query | report_req | ambiguous
    intent_confidence: float
    clarify_question: str

    retrieved_schemas: List[Dict]
    schema_context: str

    generated_sql: str
    sql_explanation: str
    sql_assumptions: List[str]
    sql_valid: bool
    sql_risk_level: str                      # safe | warning | blocked
    sql_reject_reason: str

    query_columns: List[str]
    query_rows: List[List]
    query_row_count: int
    query_elapsed_ms: float
    query_truncated: bool
    query_error: str

    interpretation: str
    highlights: List[str]
    chart_suggestion: Dict
    follow_up_questions: List[str]

    error_count: int
    recovery_path: str                       # retry | rewrite | fallback | reject

    # Report-specific fields
    report_title: str
    report_sub_queries: List[Dict]
    report_date_range: str
    report_data: List[Dict]
    report_elapsed_ms: float
