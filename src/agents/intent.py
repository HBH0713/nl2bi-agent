import json
from src.agents.state import AgentState
from src.models.router import ModelRouter, ModelTask
from src.prompts.intent import build_intent_messages
import structlog

logger = structlog.get_logger("agent.intent")


async def intent_classifier(state: AgentState, router: ModelRouter) -> dict:
    """意图分类节点 — 使用 Ollama 本地模型"""
    query = state.get("user_query", "")

    if not query.strip():
        return {
            "intent": "ambiguous",
            "intent_confidence": 0.0,
            "clarify_question": "您好！请问您想查询什么数据？",
        }

    messages = build_intent_messages(query)

    try:
        response = await router.chat_json(
            task=ModelTask.INTENT,
            messages=messages,
            temperature=0.0,
        )
        result = json.loads(response.content)

        logger.info(
            "Intent classified",
            query=query[:50],
            intent=result.get("intent"),
            confidence=result.get("confidence"),
        )

        return {
            "intent": result.get("intent", "ambiguous"),
            "intent_confidence": result.get("confidence", 0.0),
            "clarify_question": result.get("clarify_question", ""),
        }

    except Exception as e:
        logger.error("Intent classification failed", error=str(e))
        return {
            "intent": "data_query",
            "intent_confidence": 0.3,
            "clarify_question": "",
        }
