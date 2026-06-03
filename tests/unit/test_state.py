from src.agents.state import AgentState


class TestAgentState:

    def test_initial_state(self):
        state: AgentState = {
            "messages": [],
            "user_query": "上个月销售额",
            "intent": "",
            "intent_confidence": 0.0,
            "clarify_question": "",
            "retrieved_schemas": [],
            "schema_context": "",
            "generated_sql": "",
            "sql_explanation": "",
            "sql_assumptions": [],
            "sql_valid": False,
            "sql_risk_level": "",
            "sql_reject_reason": "",
            "query_columns": [],
            "query_rows": [],
            "query_row_count": 0,
            "query_elapsed_ms": 0.0,
            "query_truncated": False,
            "query_error": "",
            "interpretation": "",
            "highlights": [],
            "chart_suggestion": {},
            "follow_up_questions": [],
            "error_count": 0,
            "recovery_path": "",
        }

        assert state["user_query"] == "上个月销售额"
        assert state["error_count"] == 0
        assert state["intent"] == ""
