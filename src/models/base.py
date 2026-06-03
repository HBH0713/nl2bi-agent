from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0


class BaseLLMClient(ABC):
    """所有模型客户端的抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
    ) -> LLMResponse:
        """返回 JSON 格式响应"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...
