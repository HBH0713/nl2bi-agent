# NL2BI Agent — 学习路线图

基于本项目的实际代码，系统学习 **企业级 NL2BI 数据分析 Agent** 的核心原理。

## 学习顺序

```
第一周                第二周                第三周
┌──────────┐      ┌──────────┐      ┌──────────┐
│ 1. Agent │  ──→ │ 3. Schema│  ──→ │ 5. 对话  │
│   编排    │      │   RAG    │      │   状态   │
└──────────┘      └──────────┘      └──────────┘
     │                  │                  │
     ├──────────────────┼──────────────────┤
     │        ┌──────────┐      ┌──────────┐
     └──────→ │ 2. 混合  │      │ 4. SQL   │
              │   路由   │      │   安全   │
              └──────────┘      └──────────┘
                       │              │
                       └──────┬───────┘
                              ↓
                      ┌──────────┐
                      │ 6. Prompt│
                      │  工程    │
                      └──────────┘
```

## 文档索引

| 编号 | 文档 | 关键文件 | 难度 |
|------|------|---------|------|
| 01 | [LangGraph Agent 编排](01-langgraph-agent-orchestration.md) | `src/agents/graph.py` | ⭐⭐⭐ |
| 02 | [混合模型路由与成本优化](02-hybrid-model-routing.md) | `src/models/router.py` | ⭐⭐ |
| 03 | [Schema RAG 检索增强生成](03-schema-rag.md) | `src/rag/` (全部) | ⭐⭐⭐ |
| 04 | [SQL 安全三层校验](04-sql-security.md) | `src/agents/sql_validator.py`, `src/db/executor.py` | ⭐⭐ |
| 05 | [对话状态管理与多轮上下文](05-conversation-state.md) | `src/agents/state.py` | ⭐⭐ |
| 06 | [Prompt Engineering 实践](06-prompt-engineering.md) | `src/prompts/` (全部) | ⭐ |

## 项目架构速览

```
用户输入 (自然语言)
    │
    ▼
┌─────────────────────────────────────────────────┐
│                  LangGraph 状态图                  │
│                                                   │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐  │
│  │ 意图分类  │──→│Schema RAG│──→│ NL2SQL 生成  │  │
│  │ (Ollama) │   │(BGE+Chroma)│  │  (DeepSeek)  │  │
│  └──────────┘   └──────────┘   └──────┬───────┘  │
│       │                                │          │
│       │                                ▼          │
│       │              ┌──────────┐   ┌──────────┐  │
│       └──────────────│  闲聊    │   │ SQL 校验  │  │
│                      └──────────┘   └────┬─────┘  │
│                                          │        │
│                              ┌───────────┼─────── │
│                              ▼           ▼        │
│                         ┌────────┐ ┌──────────┐  │
│                         │ 执行   │ │ 拒绝处理  │  │
│                         └───┬────┘ └──────────┘  │
│                             │                     │
│                             ▼                     │
│                        ┌─────────┐                │
│                        │ 结果解读 │                │
│                        └─────────┘                │
└─────────────────────────────────────────────────┘
    │
    ▼
 结构化响应 (JSON) → Streamlit 前端渲染
```

## 运行本项目

```bash
# 1. 启动 PostgreSQL
pg_ctl start -D /c/Users/86135/pgdata

# 2. 启动后端
cd C:/Users/86135/nl2bi-agent
uvicorn src.main:app --port 8000 --host 0.0.0.0

# 3. 启动前端
streamlit run src/app.py --server.port 8501

# 4. 访问 http://localhost:8501
```

## 技术栈一览

| 层 | 技术 | 作用 |
|----|------|------|
| Agent 编排 | LangGraph | 状态图、节点路由、断点恢复 |
| API | FastAPI | REST 接口、CORS、中间件 |
| 精度模型 | DeepSeek V3 (OpenAI 兼容) | NL2SQL 生成、结果解读 |
| 轻量模型 | Ollama + Qwen 2.5 7B | 意图分类、SQL 校验 |
| 嵌入模型 | BGE-small-zh-v1.5 | 中文文本向量化 |
| 向量库 | ChromaDB | Schema 语义检索 |
| 数据库 | PostgreSQL 16 + pgvector | 业务数据存储 |
| SQL 解析 | SQLGlot | 语法解析 + 安全检查 |
| 前端 | Streamlit + Plotly | Web UI + 图表 |
| 日志 | structlog (JSON) | 结构化日志 |
| 部署 | Docker Compose | 容器化 |
