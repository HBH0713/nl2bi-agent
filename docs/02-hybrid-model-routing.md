# 02 — 混合模型路由与成本优化

> 关键文件：`src/models/router.py`（88行） + `src/models/openai_compat.py`（112行） + `src/models/ollama.py`（68行） + `src/models/base.py`（38行）

## 核心思想

**不同任务需要不同精度级别，不同精度对应不同成本。**

```
低精度任务（免费本地模型）              高精度任务（按量付费 API）
┌─────────────────────┐           ┌─────────────────────┐
│ Ollama + Qwen 7B    │           │ DeepSeek V3 / GPT-4o │
│                     │           │                     │
│ • 意图分类          │           │ • NL2SQL 生成       │
│ • Schema RAG 改写   │           │ • 结果解读          │
│ • SQL 语义校验      │           │                     │
│ • 闲聊回复          │           │                     │
│                     │           │                     │
│ 成本: $0            │           │ 成本: ~$0.0002/次   │
│ 延迟: 1~2s          │           │ 延迟: 2~5s          │
└─────────────────────┘           └─────────────────────┘
```

---

## 架构设计

### 1. 抽象基类

```python
class BaseLLMClient(ABC):
    @abstractmethod
    async def chat(self, messages, temperature, max_tokens) -> LLMResponse: ...
    @abstractmethod
    async def chat_json(self, messages, temperature) -> LLMResponse: ...
    @property
    @abstractmethod
    def model_name(self) -> str: ...
```

所有模型客户端实现同一接口，上层代码不需要关心底层是 Ollama 还是 OpenAI。

### 2. Ollama 客户端

```python
class OllamaClient(BaseLLMClient):
    def __init__(self, base_url="http://localhost:11434", model="qwen2.5:7b"):
        ...

    @async_retry(max_retries=2, base_delay=0.5)    # ← 最多重试2次
    async def chat(self, messages, temperature, max_tokens) -> LLMResponse:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{self._base_url}/api/chat", json={...})
            ...

    async def chat_json(self, messages, temperature) -> LLMResponse:
        # Qwen 不支持原生 JSON mode → 在 system prompt 末尾追加指令
        messages_with_json = messages.copy()
        messages_with_json.append({
            "role": "system",
            "content": "你必须只返回有效的 JSON，不要包含任何其他文字..."
        })
        return await self.chat(messages_with_json, temperature)
```

**关键细节**：Ollama 不支持 `response_format: json_object`，所以靠 Prompt 约束来模拟 JSON 输出。

### 3. OpenAI 兼容客户端

```python
class OpenAICompatClient(BaseLLMClient):
    def __init__(self, api_key, model="deepseek-chat", base_url="https://api.deepseek.com"):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def _estimate_cost(self, prompt_tokens, completion_tokens) -> float:
        # 按模型定价表计算
        pricing = MODEL_PRICING.get(self._model)
        cost = (prompt_tokens * pricing["input"] +
                completion_tokens * pricing["output"]) / 1_000_000
        return round(cost, 6)

    @async_retry(max_retries=3, base_delay=1.0)    # ← 可重试3次（比Ollama多1次，API更稳定）
    async def chat(self, messages, temperature, max_tokens) -> LLMResponse:
        response = await self._client.chat.completions.create(...)
        cost = self._estimate_cost(prompt_tokens, completion_tokens)
        return LLMResponse(content=..., cost_usd=cost, ...)

    async def chat_json(self, messages, temperature) -> LLMResponse:
        # DeepSeek 支持原生 JSON mode
        response = await self._client.chat.completions.create(
            ...,
            response_format={"type": "json_object"}    # ← 原生约束
        )
```

**关键细节**：每次调用都记录 Token 消耗和费用，方便成本追踪。

---

## 路由器：任务 → 模型映射

```python
class ModelTask(str, Enum):
    INTENT = "intent"           # 意图分类
    SCHEMA_RAG_QUERY = "schema_rag"
    NL2SQL = "nl2sql"           # SQL 生成
    SQL_VALIDATE = "sql_validate"
    INTERPRET = "interpret"     # 结果解读
    CHITCHAT = "chitchat"

TASK_ROUTING = {
    ModelTask.INTENT: "ollama",         # 本地免费模型
    ModelTask.SCHEMA_RAG_QUERY: "ollama",
    ModelTask.NL2SQL: "api",            # 云端付费 API
    ModelTask.SQL_VALIDATE: "ollama",
    ModelTask.INTERPRET: "api",
    ModelTask.CHITCHAT: "ollama",
}
```

**路由决策逻辑**：

| 任务 | 选 Ollama 的理由 | 选 API 的理由 |
|------|-----------------|-------------|
| 意图分类 | 简单分类，7B 足够 | — |
| Schema RAG | 改写查询，容错率高 | — |
| **NL2SQL** | — | **SQL 语法严格，容错率 0** |
| SQL 校验 | 辅助检查，非关键路径 | — |
| 结果解读 | — | 需要高质量中文表达 |
| 闲聊 | 非业务任务，免费就好 | — |

---

## API 失败降级（Fallback）

```python
async def chat(self, task, messages, temperature, max_tokens, fallback_on_failure=True):
    client = self._get_client(task)

    try:
        response = await client.chat(messages, temperature, max_tokens)
        return response
    except Exception as e:
        if fallback_on_failure and client == self._api:
            # DeepSeek 挂了 → 降级到本地 Ollama
            logger.warning("API failed, falling back to Ollama", task=task.value, error=str(e))
            response = await self._ollama.chat(messages, temperature, max_tokens)
            response.cost_usd = 0.0
            return response
        raise
```

**降级策略**：只降级不升级（API → Ollama 可以，Ollama → API 不行）。

---

## 重试机制

```python
def async_retry(max_retries=3, base_delay=1.0, max_delay=30.0, backoff_factor=2.0):
    """指数退避重试"""
    # 第1次失败 → 等 1s → 重试
    # 第2次失败 → 等 2s → 重试
    # 第3次失败 → 等 4s → 重试
    # 全部失败 → 抛出异常
```

**指数退避公式**：`delay = min(base_delay * (backoff_factor ^ attempt), max_delay)`

| 重试次数 | 延迟 | 累计等待 |
|---------|------|---------|
| 1 | 1.0s | 1.0s |
| 2 | 2.0s | 3.0s |
| 3 | 4.0s | 7.0s |

---

## 成本模型

```python
MODEL_PRICING = {
    "deepseek-chat":    {"input": 0.14, "output": 0.28},   # $/百万 token
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    "gpt-4o":           {"input": 2.50, "output": 10.00},
    "gpt-4o-mini":      {"input": 0.15, "output": 0.60},
}
```

**单次查询成本估算**（以本项目为例）：

```
意图分类:     Ollama → $0
Schema RAG:   Ollama → $0
NL2SQL:       500 in + 200 out = (500*0.14 + 200*0.28)/1M = $0.000126
SQL 校验:     Ollama → $0
结果解读:     300 in + 400 out = (300*0.14 + 400*0.28)/1M = $0.000154
─────────────────────────────────────────────────────────
总计: ~$0.00028/次  ≈ 0.002 元/次
```

**如果用全 API 栈（无 Ollama）**，成本约 $0.002/次（7倍）。**如果 7B 模型处理 SQL 生成出错导致重试**，可能反而更贵。

---

## 关键学习点

1. **按任务精度需求路由**，而非一刀切用同一个模型
2. **抽象基类统一接口**，换模型不改上层代码
3. **API 失败降级到本地**，保证可用性（体验可能变差，但不会挂）
4. **指数退避重试**，避免瞬时错误导致失败
5. **每次调用记录 Token→费用**，成本可追踪
6. **本地模型用 Prompt 模拟 JSON mode**，云端用 `response_format`

### 进阶方向

- 动态路由：根据意图置信度决定用哪个模型（低置信度 → 强模型澄清）
- 缓存策略：相同/相似问题复用 SQL（已实现在 `src/utils/cache.py`）
- 模型性能基准：统计各模型在各类任务上的准确率
