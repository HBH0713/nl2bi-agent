import time
import httpx
from src.models.base import BaseLLMClient, LLMResponse
from src.utils.retry import async_retry
import structlog

logger = structlog.get_logger("ollama")


class OllamaClient(BaseLLMClient):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:7b"):
        self._base_url = base_url.rstrip("/")
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    @async_retry(max_retries=2, base_delay=0.5, exceptions=(httpx.HTTPError,))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        start = time.time()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        latency = (time.time() - start) * 1000
        content = data["message"]["content"]
        tokens = data.get("eval_count", 0)

        logger.info("Ollama chat completed", model=self._model, tokens=tokens, latency_ms=round(latency))

        return LLMResponse(
            content=content,
            model=self._model,
            tokens_used=tokens,
            latency_ms=latency,
            cost_usd=0.0,
        )

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> LLMResponse:
        messages_with_json = messages.copy()
        messages_with_json.append({
            "role": "system",
            "content": "你必须只返回有效的 JSON，不要包含任何其他文字或 markdown 代码块标记。"
        })
        return await self.chat(messages_with_json, temperature=temperature)
