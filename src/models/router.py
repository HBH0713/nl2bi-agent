from enum import Enum
from src.models.base import BaseLLMClient, LLMResponse
from src.models.ollama import OllamaClient
from src.models.openai_compat import OpenAICompatClient
import structlog

logger = structlog.get_logger("model_router")


class ModelTask(str, Enum):
    INTENT = "intent"
    SCHEMA_RAG_QUERY = "schema_rag"
    NL2SQL = "nl2sql"
    SQL_VALIDATE = "sql_validate"
    INTERPRET = "interpret"
    CHITCHAT = "chitchat"


TASK_ROUTING = {
    ModelTask.INTENT: "ollama",
    ModelTask.SCHEMA_RAG_QUERY: "ollama",
    ModelTask.NL2SQL: "api",
    ModelTask.SQL_VALIDATE: "ollama",
    ModelTask.INTERPRET: "api",
    ModelTask.CHITCHAT: "ollama",
}


class ModelRouter:
    """按任务类型路由到不同模型，支持 API 失败时降级到 Ollama"""

    def __init__(self, ollama: OllamaClient, api: OpenAICompatClient):
        self._ollama = ollama
        self._api = api

    def _get_client(self, task: ModelTask) -> BaseLLMClient:
        backend = TASK_ROUTING.get(task, "ollama")
        return self._api if backend == "api" else self._ollama

    async def chat(
        self,
        task: ModelTask,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
        fallback_on_failure: bool = True,
    ) -> LLMResponse:
        client = self._get_client(task)
        backend_used = "api" if client == self._api else "ollama"

        try:
            response = await client.chat(messages, temperature, max_tokens)
            logger.info("Model routed", task=task.value, backend=backend_used, status="success")
            return response
        except Exception as e:
            if fallback_on_failure and client == self._api:
                logger.warning("API failed, falling back to Ollama", task=task.value, error=str(e))
                response = await self._ollama.chat(messages, temperature, max_tokens)
                response.cost_usd = 0.0
                return response
            raise

    async def chat_json(
        self,
        task: ModelTask,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        fallback_on_failure: bool = True,
    ) -> LLMResponse:
        client = self._get_client(task)

        try:
            response = await client.chat_json(messages, temperature)
            logger.info("Model routed (JSON)", task=task.value, backend="api" if client == self._api else "ollama")
            return response
        except Exception as e:
            if fallback_on_failure and client == self._api:
                logger.warning("API JSON failed, falling back to Ollama", task=task.value, error=str(e))
                return await self._ollama.chat_json(messages, temperature)
            raise

    @property
    def ollama(self) -> OllamaClient:
        return self._ollama

    @property
    def api(self) -> OpenAICompatClient:
        return self._api
