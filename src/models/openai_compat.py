import time
from openai import AsyncOpenAI
from src.models.base import BaseLLMClient, LLMResponse
from src.utils.retry import async_retry
import structlog

logger = structlog.get_logger("openai_compat")

MODEL_PRICING = {
    "deepseek-chat": {"input": 0.14, "output": 0.28},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


class OpenAICompatClient(BaseLLMClient):
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
    ):
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @property
    def model_name(self) -> str:
        return self._model

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        pricing = MODEL_PRICING.get(self._model, {"input": 1.0, "output": 2.0})
        cost = (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000
        return round(cost, 6)

    @async_retry(max_retries=3, base_delay=1.0, exceptions=(Exception,))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        start = time.time()

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        latency = (time.time() - start) * 1000
        choice = response.choices[0]
        content = choice.message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        cost = self._estimate_cost(prompt_tokens, completion_tokens)

        logger.info(
            "OpenAI-compat chat completed",
            model=self._model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency),
            cost_usd=cost,
        )

        return LLMResponse(
            content=content,
            model=self._model,
            tokens_used=prompt_tokens + completion_tokens,
            latency_ms=latency,
            cost_usd=cost,
        )

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> LLMResponse:
        start = time.time()

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )

        latency = (time.time() - start) * 1000
        choice = response.choices[0]
        content = choice.message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        cost = self._estimate_cost(prompt_tokens, completion_tokens)

        logger.info(
            "OpenAI-compat JSON chat completed",
            model=self._model,
            tokens=prompt_tokens + completion_tokens,
            latency_ms=round(latency),
            cost_usd=cost,
        )

        return LLMResponse(
            content=content,
            model=self._model,
            tokens_used=prompt_tokens + completion_tokens,
            latency_ms=latency,
            cost_usd=cost,
        )
