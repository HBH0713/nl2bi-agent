# 01 — LangGraph Agent 编排

> 关键文件：`src/agents/graph.py`（176行） + `src/agents/state.py`（42行）

## 核心概念

### 什么是 Agent？

Agent = LLM + 工具 + 决策循环。与传统"调用一次 LLM 得到结果"不同，Agent 会在多个步骤之间做出决策，根据中间结果决定下一步做什么。

### LangGraph 的三个核心抽象

```
┌────────────────────────────────────────────┐
│                  StateGraph                 │
│                                             │
│   State────→[Node A]────→[Node B]────→END  │
│    ↑           │              │             │
│    └─── 共享状态在节点间流转 ──┘             │
│                                             │
│   Checkpoint: 每个节点执行后自动保存状态快照  │
└────────────────────────────────────────────┘
```

#### 1. State（状态）

`AgentState` 是一个 `TypedDict`，包含整个对话流程中所有需要传递的数据：

```python
class AgentState(TypedDict):
    # 输入
    user_query: str                          # 用户原始问题
    messages: Annotated[List[Any], add_messages]  # 对话历史（自动追加）

    # 意图
    intent: str                              # chitchat | data_query | report_req | ambiguous
    intent_confidence: float

    # RAG 检索
    schema_context: str                      # 检索到的表结构文本

    # SQL 生成
    generated_sql: str                       # LLM 生成的 SQL
    sql_explanation: str                     # SQL 的中文解释
    sql_valid: bool                          # 是否通过校验

    # 执行结果
    query_rows: List[List]                   # 查询结果行
    query_columns: List[str]                 # 列名

    # 输出
    interpretation: str                      # 自然语言解读
    highlights: List[str]                    # 关键发现
    chart_suggestion: Dict                   # 图表推荐
    follow_up_questions: List[str]           # 推荐追问

    # 错误恢复
    error_count: int                         # 累计错误次数
    recovery_path: str                       # retry | rewrite | fallback | reject
```

**关键理解**：State 不是全局变量，而是在节点间传递的**不可变快照**。每个节点返回的是一个 Dict，LangGraph 自动将其合并到当前 State。

#### 2. Node（节点）

每个节点是一个异步函数，签名为：

```python
async def node_function(state: AgentState, ...) -> dict:
    # 从 state 中读取需要的数据
    # 执行业务逻辑
    # 返回要更新的字段
    return {"field_name": new_value}
```

节点返回的 Dict 会被 **浅合并**到当前 State（只更新有变化的字段）。

#### 3. Edge（边）

三种边类型：

| 类型 | 代码 | 说明 |
|------|------|------|
| 普通边 | `workflow.add_edge("A", "B")` | A 执行完无条件进入 B |
| 条件边 | `workflow.add_conditional_edges("A", router, {...})` | 根据 State 动态选择下一节点 |
| 入口边 | `workflow.set_entry_point("A")` | 指定起始节点 |

---

## 本项目 Graph 详解

### 完整流转图

```
                        ┌──────────────┐
                        │   用户输入    │
                        └──────┬───────┘
                               │
                        ┌──────▼───────┐
                        │ intent_      │
                        │ classifier   │  ← Ollama (免费)
                        └──────┬───────┘
                               │ route_after_intent
                ┌──────────────┼──────────────────┐
                │              │                  │
         chitchat         data_query/        report_req
                │         ambiguous              │
                │              │                  │
        ┌───────▼──┐   ┌──────▼──────┐   ┌──────▼──────┐
        │chitchat  │   │ schema_rag  │   │report_      │
        │_handler  │   │             │   │planner      │
        └────┬─────┘   └──────┬──────┘   └──────┬──────┘
             │                │                  │
             │         ┌──────▼──────┐   ┌──────▼──────┐
             │         │sql_generator│   │report_runner│
             │         │ (DeepSeek)  │   │             │
             │         └──────┬──────┘   └──────┬──────┘
             │                │                  │
             │         ┌──────▼──────┐           │
             │         │sql_validator│           │
             │         └──────┬──────┘           │
             │                │ route_after_validate
             │           ┌────┴────┐
             │      executor   reject_handler
             │           │          │
             │       route_after_execute
             │      ┌────┴────┐
             │ interpreter  reject_handler
             │      │
             └──────┴────────→ END
```

### 路由函数详解

#### 路由 1：意图分流

```python
def route_after_intent(state: AgentState) -> Literal["chitchat_handler", "schema_rag", "report_handler"]:
    intent = state.get("intent", "ambiguous")
    if intent == "chitchat":
        return "chitchat_handler"     # 闲聊 → 直接回复
    elif intent == "report_req":
        return "report_handler"       # 报表请求 → 报表规划
    else:
        return "schema_rag"           # 数据查询 → Schema 检索
```

#### 路由 2：SQL 校验分流

```python
def route_after_validate(state: AgentState) -> Literal["executor", "reject_handler"]:
    if state.get("sql_valid", False):
        return "executor"             # 通过 → 执行 SQL
    return "reject_handler"           # 失败 → 错误处理
```

#### 路由 3：执行结果分流

```python
def route_after_execute(state: AgentState) -> Literal["interpreter", "reject_handler"]:
    if state.get("query_error", ""):
        return "reject_handler"       # 执行出错 → 错误处理
    return "interpreter"              # 成功 → 结果解读
```

---

## 错误恢复机制

```
  ┌──────────────┐    第1次失败     ┌───────────────┐
  │ sql_generator │ ──────────────→ │ reject_handler │
  └──────────────┘                  └───────┬───────┘
                                            │ error_count=1, recovery_path="rewrite"
                                            │ "正在尝试重新理解您的需求..."
                                   ┌────────▼────────┐
                                   │  自动重新执行     │
                                   │  sql_generator   │  ← 带着错误反馈重新生成
                                   └────────┬────────┘
                                            │ 第2次失败
                                   ┌────────▼────────┐
                                   │ reject_handler   │
                                   │ error_count=2    │
                                   │ recovery_path=   │
                                   │ "fallback"       │
                                   │ "多次尝试仍无法   │
                                   │  处理，建议..."  │
                                   └─────────────────┘
```

关键代码：

```python
async def reject_handler(state: AgentState) -> dict:
    error_count = state.get("error_count", 0) + 1

    if error_count >= 2:
        # 达到最大重试次数 → 提供友好建议
        return {
            "error_count": error_count,
            "recovery_path": "fallback",
            "interpretation": "很抱歉，我多次尝试仍无法正确处理您的查询...",
        }

    # 第一次失败 → 提示用户并允许重试
    return {
        "error_count": error_count,
        "recovery_path": "rewrite",
        "interpretation": f"查询处理遇到问题：{reason}。正在尝试重新理解...",
    }
```

---

## Checkpoint（检查点）

```python
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
return workflow.compile(checkpointer=memory)
```

`MemorySaver` 在每个节点执行后保存 State 快照。实际效果：

1. **多轮对话**：每次调用传入 `thread_id`，LangGraph 自动加载历史 State
2. **断点恢复**：可以从中断处继续执行
3. **调试利器**：可以回到任意节点查看当时的状态

---

## 关键学习点

1. **状态驱动设计**：所有数据通过 State 传递，节点函数纯函数化（输入 State，输出部分更新）
2. **条件路由 > if/else**：用图的条件边替代代码中的复杂分支，流程图就是代码
3. **错误恢复靠重试 + 状态累积**：`error_count` 递增，每次重试带上次的错误信息
4. **节点是异步的**：每个节点都是一个 `async def`，天然支持并发 I/O
5. **小步快跑**：每个节点只做一件事（分类、检索、生成、校验、执行、解读），职责单一

### 进阶阅读

- LangGraph 官方文档：[langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/)
- 核心概念：`StateGraph`, `add_node`, `add_edge`, `add_conditional_edges`, `checkpointer`
- 本项目对比参考：理解为什么不用 LangChain 的 AgentExecutor 而直接用 LangGraph（更灵活的路由控制）
