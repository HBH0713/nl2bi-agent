# NL2BI Agent — 企业级自然语言数据分析平台

基于 LangGraph + FastAPI 构建的企业级 NL2BI 数据分析 Agent，支持自然语言转 SQL、多轮对话分析，采用本地+云端混合模型架构。

## 快速开始

### 环境要求
- Python 3.11+
- Docker & Docker Compose
- DeepSeek API Key（或其他 OpenAI 兼容 API）

### 1. 克隆并配置

```bash
git clone <repo-url>
cd nl2bi-agent
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY
```

### 2. 初始化环境

```bash
pip install -e ".[dev]"
bash scripts/init_db.sh
```

### 3. 启动服务

```bash
# Docker 全栈启动
docker compose up -d

# 或本地开发
uvicorn src.main:app --reload
```

### 4. 测试

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "上个月各区域的销售额是多少？"}'
```

### 5. API 文档

启动服务后访问 http://localhost:8000/docs 查看 Swagger 文档。

## 架构概览

```
用户输入 → 意图分类(Ollama) → Schema RAG → NL2SQL(DeepSeek) → SQL校验 → 执行 → 结果解读
```

### Agent 状态流转

| 节点 | 模型 | 说明 |
|------|------|------|
| Intent Classifier | Ollama Qwen 2.5 7B | 分类用户意图（查数据/要报表/闲聊/模糊） |
| Schema RAG | BGE Embedding | 检索相关表结构供 LLM 使用 |
| NL2SQL Generator | DeepSeek/GPT-4o | 生成 PostgreSQL SELECT 语句 |
| SQL Validator | SQLGlot + Ollama | 三层安全校验（语法/规则/语义） |
| SQL Executor | PostgreSQL | 沙箱执行（只读、超时、行数限制） |
| Interpreter | DeepSeek/GPT-4o | 结果解读 + 图表推荐 |

## 项目结构

```
src/
├── agents/     # LangGraph Agent 节点
├── models/     # 模型抽象层（Ollama + API + 路由器）
├── db/         # PostgreSQL + ChromaDB
├── rag/        # Schema 向量化 + 混合检索
├── api/        # FastAPI 路由 + 中间件
├── utils/      # SQL 解析 + 重试 + 日志
└── prompts/    # Prompt 模板
```

## 技术栈

| 层 | 技术 |
|----|------|
| Agent 编排 | LangGraph |
| API | FastAPI |
| 数据库 | PostgreSQL + pgvector |
| 向量库 | ChromaDB |
| 模型（精度） | DeepSeek / GPT-4o |
| 模型（轻量） | Ollama + Qwen 2.5 7B |
| 安全 | SQLGlot + 规则引擎 + DB 沙箱 |
| 可观测 | structlog (JSON) |
| 部署 | Docker Compose |

## 运行测试

```bash
# 单元测试（无需外部服务）
pytest tests/unit/ -v

# 所有测试
pytest -v
```

## License

MIT
