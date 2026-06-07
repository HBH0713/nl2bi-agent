# 03 — Schema RAG 检索增强生成

> 关键文件：`src/rag/embedder.py` + `src/rag/schema_indexer.py` + `src/rag/retriever.py` + `src/agents/schema_rag.py` + `src/db/chroma_client.py`

## 为什么需要 Schema RAG？

LLM 不认识你的数据库。你需要告诉它：

1. 有哪些表
2. 每个表有哪些字段、什么类型
3. 业务术语的含义（"销售额"对应哪个字段）

**朴素方案**：把所有表结构塞进 Prompt
**问题**：表多了（100+ 张），Token 超限、成本飙升、无关信息干扰模型

**RAG 方案**：先检索再注入，只给最相关的表结构

```
用户问 "上个月华东区销售额"
        │
        ▼
┌───────────────────┐
│ 1. 查询向量化      │  BGE-small-zh-v1.5 将问题转为 512 维向量
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ 2. 相似度检索      │  ChromaDB 向量搜索 → Top-K 最相关文档
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ 3. Context 组装   │  表结构 + 字段描述 + 业务术语 → 格式化文本
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ 4. 注入 Prompt    │  拼接到 SQL 生成的 System Prompt 中
└───────────────────┘
```

---

## 三层索引策略

### 第一层：表级别

```
文档 ID:  table_orders
文本:     "表 orders: 订单信息表。字段包括: order_id(订单唯一标识),
          customer_id(关联客户ID), total_amount(订单总金额，含税),
          order_date(下单日期), status(订单状态)。大约 50000 行数据。"
类型:     table
```

### 第二层：字段级别

```
文档 ID:  col_orders_total_amount
文本:     "字段 orders.total_amount: 订单总金额，类型 DECIMAL(12,2)。
          示例值: [128.50, 399.00, 56.80]"
类型:     column
```

### 第三层：业务术语

```
文档 ID:  term_销售额
文本:     "业务术语「销售额」: 已支付订单的总金额合计。
          SQL 写法: SUM(orders.total_amount) WHERE orders.status = 'delivered'"
类型:     business_term
```

**三层互补**：
- 表级 → 回答"数据在哪张表"
- 字段级 → 回答"用哪个字段"
- 术语级 → 回答"业务概念怎么映射到 SQL"

---

## 嵌入模型

```python
class Embedder:
    def __init__(self, model_name="BAAI/bge-small-zh-v1.5"):
        # local_files_only=True → 不联网检查更新（国内网络必备）
        self._model = SentenceTransformer(model_name, local_files_only=True)
        self._dimension = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
```

**BGE-small-zh-v1.5 特点**：

| 属性 | 值 |
|------|-----|
| 维度 | 512 |
| 模型大小 | ~100MB |
| 中文优化 | ✅ |
| 归一化 | `normalize_embeddings=True` → 余弦相似度 |
| 本地加载 | `local_files_only=True` |

> **⚠️ 踩坑记录**：`local_files_only=False`（默认）时，SentenceTransformer 会尝试连接 huggingface.co 检查模型更新。国内网络下这会导致 WinError 10060 超时 + 5 次重试，每次请求卡死约 2 分钟。务必设为 True。

---

## 向量检索

```python
def hybrid_search(query: str, top_k: int = 10, table_filter=None) -> List[Dict]:
    embedder = get_embedder()
    collection = get_or_create_collection("schema_embeddings")

    # 1. 将查询转为向量
    query_embedding = embedder.embed_single(query)

    # 2. ChromaDB 相似度搜索
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,        # 可选：按 metadata 过滤
        include=["documents", "metadatas", "distances"],
    )

    # 3. 组装返回
    documents = []
    for i in range(len(results["ids"][0])):
        documents.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return documents
```

---

## Context 组装（build_schema_context）

这是连接 RAG 和 LLM 的桥梁：

```python
def build_schema_context(query: str, top_tables: int = 5) -> str:
    results = hybrid_search(query, top_k=top_tables * 3)  # 检索 3 倍再筛选

    # Step 1: 提取 TOP-N 表（去重）
    seen_tables = set()
    table_docs = []
    for doc in results:
        if doc["metadata"].get("type") == "table":
            table_name = doc["metadata"].get("table_name", "")
            if table_name not in seen_tables:
                seen_tables.add(table_name)
                table_docs.append(doc)
                if len(table_docs) >= top_tables:
                    break

    # Step 2: 提取业务术语
    business_terms = [doc["text"] for doc in results
                      if doc["metadata"].get("type") == "business_term"]

    # Step 3: 拼接
    parts = []
    if table_docs:
        parts.append("=== 相关数据表 ===")
        for doc in table_docs:
            parts.append(doc["text"])
    if business_terms:
        parts.append("\n=== 相关业务术语 ===")
        for term_text in business_terms[:5]:
            parts.append(f"- {term_text}")

    return "\n".join(parts)
```

**输出示例**：

```
=== 相关数据表 ===
表 orders: 订单信息表。字段包括: ...
表 customers: 客户信息表。字段包括: ...

=== 相关业务术语 ===
- 业务术语「销售额」: 已支付订单的总金额合计。SQL 写法: SUM(orders.total_amount) WHERE ...
- 业务术语「华东区」: customers.region = '华东'
```

这个字符串会被注入到 SQL 生成的 Prompt 中，放在 "## 可用的数据库 Schema" 下面。

---

## 索引构建流程

```python
def index_schemas(metadata_path="data/schema_metadata.json", reset=False):
    # 1. 读取 metadata JSON
    documents = build_schema_texts(metadata_path)

    # 2. 批量向量化
    texts = [d["text"] for d in documents]
    embeddings = embedder.embed(texts)    # 全文批量编码

    # 3. 写入 ChromaDB（分批，每批 100 个）
    for i in range(0, len(documents), 100):
        collection.add(
            ids=ids[i:batch_end],
            embeddings=embeddings[i:batch_end],
            metadatas=metadatas[i:batch_end],
            documents=texts[i:batch_end],
        )
```

---

## Schema Metadata 数据结构

索引的数据来源：`data/schema_metadata.json`

```json
{
  "tables": [
    {
      "table_name": "orders",
      "description": "订单信息表",
      "row_count_estimate": 50000,
      "columns": [
        {
          "name": "order_id",
          "type": "SERIAL",
          "description": "订单唯一标识",
          "sample_values": [1001, 1002, 1003]
        },
        {
          "name": "total_amount",
          "type": "DECIMAL(12,2)",
          "description": "订单总金额（含税）",
          "sample_values": [128.50, 399.00, 56.80]
        }
      ]
    }
  ],
  "business_terms": [
    {
      "term": "销售额",
      "description": "已支付订单的总金额合计",
      "sql_fragment": "SUM(orders.total_amount) WHERE orders.status = 'delivered'"
    }
  ]
}
```

---

## Agent 中的集成

在 `schema_rag_retriever` 节点中，会结合对话历史构造搜索查询：

```python
async def schema_rag_retriever(state: AgentState) -> dict:
    query = state.get("user_query", "")
    recent_messages = [m for m in state["messages"][-4:] if m.content]
    history_context = " ".join(m.content for m in recent_messages)

    # 把对话历史也加入搜索，理解上下文指代
    search_query = f"{query} {history_context}" if history_context else query

    schema_context = build_schema_context(search_query, top_tables=5)
    return {"schema_context": schema_context}
```

---

## 关键学习点

1. **嵌入模型选型**：中文场景用 BGE，英文用 all-MiniLM，维度越低越快
2. **三级索引互补**：表 → 字段 → 术语，覆盖"在哪 → 怎么查 → 什么意思"三层需求
3. **`local_files_only=True`**：国内部署必须，避免 HuggingFace 超时
4. **检索 3 倍再筛选**：向量召回可能有噪声，多召回再按规则过滤
5. **Context 格式化**：检索结果不能直接丢给 LLM，需要结构化拼接
6. **对话历史参与检索**：多轮对话中"那上周呢？"需要结合上文才能正确检索

### 进阶方向

- **HyDE（假设文档嵌入）**：先让 LLM 生成假设的 SQL，再用 SQL 做向量检索
- **Reranker**：用 Cross-Encoder 对 Top-K 做精排
- **Query Rewriting**：用 LLM 改写用户问题，拆分复杂查询为多个子查询分别检索
- **动态 Schema 更新**：数据库新增表/字段后自动更新索引
