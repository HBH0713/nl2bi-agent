"""
=============================================================================
  Vanna 学习 Demo — 用你的 bi_demo 数据库对比学习 Vanna RAG 架构
=============================================================================

Vanna 核心流程：
  1. train(ddl=..., documentation=..., sql=...)  ->  向量化训练数据 -> ChromaDB
  2. ask("问题")                                    ->  RAG检索 -> 拼Prompt -> LLM生成SQL -> 执行

与你项目的对比：
  +------------------------+-----------------------+-----------------------┐
  |        环节           |     你的项目         |       Vanna          |
  |-----------------------┼---------------------┼----------------------┤
  | Schema 向量化         | schema_indexer.py   | train(ddl=...)       |
  | 向量存储              | ChromaDB (手动)      | ChromaDB (内置)      |
  | 检索                  | build_schema_context | get_related_ddl()    |
  | Prompt 组装           | build_sql_gen_msgs() | get_sql_prompt()     |
  | LLM 调用              | ModelRouter          | DeepSeekChat         |
  | SQL 执行              | executor.py          | run_sql()            |
  | 安全校验              | 三层 (SQLGlot+规则+LLM) | is_sql_valid()    |
  '------------------------+-----------------------+-----------------------┘

运行方式：
  python scripts/learn_vanna.py
=============================================================================
"""

import os
import sys

# 使用项目已有的 .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

from vanna.legacy.chromadb import ChromaDB_VectorStore
from vanna.legacy.deepseek import DeepSeekChat
import psycopg2


# ═══════════════════════════════════════════════════════════════════════
# Step 1: 组合 Vanna 类（多继承模式 — Vanna 的核心设计）
# ═══════════════════════════════════════════════════════════════════════

class MyVanna(ChromaDB_VectorStore, DeepSeekChat):
    """
    Vanna 使用 Mixin 多继承模式：
    - ChromaDB_VectorStore  ->  向量存储 + RAG 检索
    - DeepSeekChat          ->  LLM 调用

    两个父类都继承自 VannaBase，所以核心方法（train/ask/get_sql_prompt）
    在 VannaBase 中定义，父类各司其职提供具体实现。

    对比你的项目：你需要手动协调 embedder + retriever + router
    Vanna 的做法：多继承自动组合，一个类搞定
    """
    def __init__(self, config=None):
        ChromaDB_VectorStore.__init__(self, config=config)
        DeepSeekChat.__init__(self, config=config)


# ═══════════════════════════════════════════════════════════════════════
# Step 2: 创建实例
# ═══════════════════════════════════════════════════════════════════════

vn = MyVanna(config={
    "api_key": os.getenv("DEEPSEEK_API_KEY"),
    "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
    "path": "./chroma_data_vanna",  # ChromaDB 持久化路径（独立于你项目的 chroma_data）
})


# ═══════════════════════════════════════════════════════════════════════
# Step 3: 连接你的 PostgreSQL 数据库
# ═══════════════════════════════════════════════════════════════════════

vn.connect_to_postgres(
    host=os.getenv("PG_HOST", "localhost"),
    dbname=os.getenv("PG_DATABASE", "bi_demo"),
    user=os.getenv("PG_USER", "bi_agent"),
    password=os.getenv("PG_PASSWORD", "changeme"),
    port=int(os.getenv("PG_PORT", "5432")),
)

print("[OK] Connected to PostgreSQL: bi_demo")


# ═══════════════════════════════════════════════════════════════════════
# Step 4: 训练 — 这是 Vanna 最核心的概念
# ═══════════════════════════════════════════════════════════════════════
#
# Vanna 的 train() 支持三种训练数据：
#
#   1. DDL（表结构）         ->  让 Vanna 认识你的表
#   2. Documentation（文档） ->  业务含义解释
#   3. SQL 示例             ->  教 Vanna 怎么写 SQL
#
# 每种数据都会被向量化存入 ChromaDB，ask() 时 RAG 检索最相关的。

print("\n" + "=" * 70)
print("开始训练 Vanna...")
print("=" * 70)

# --- 4a. 训练 DDL ---
# Vanna 通过 CREATE TABLE 语句理解表结构
vn.train(ddl="""
CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    region        VARCHAR(20)  NOT NULL,
    province      VARCHAR(50),
    city          VARCHAR(50),
    channel       VARCHAR(20),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE customers IS '客户信息表';
""")

vn.train(ddl="""
CREATE TABLE orders (
    order_id      SERIAL PRIMARY KEY,
    customer_id   INT NOT NULL REFERENCES customers(customer_id),
    order_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount  DECIMAL(12, 2) NOT NULL,
    discount_amount DECIMAL(12, 2) DEFAULT 0,
    region        VARCHAR(20),
    channel       VARCHAR(20)
);
COMMENT ON TABLE orders IS '订单表：status 包括 pending/confirmed/shipped/delivered/cancelled/returned';
""")

vn.train(ddl="""
CREATE TABLE products (
    product_id    SERIAL PRIMARY KEY,
    product_name  VARCHAR(200) NOT NULL,
    category      VARCHAR(50)  NOT NULL,
    unit_price    DECIMAL(10, 2) NOT NULL,
    cost_price    DECIMAL(10, 2) NOT NULL,
    supplier      VARCHAR(100),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
COMMENT ON TABLE products IS '产品信息表';
""")

vn.train(ddl="""
CREATE TABLE order_items (
    item_id       SERIAL PRIMARY KEY,
    order_id      INT NOT NULL REFERENCES orders(order_id),
    product_id    INT NOT NULL REFERENCES products(product_id),
    quantity      INT NOT NULL,
    unit_price    DECIMAL(10, 2) NOT NULL,
    subtotal      DECIMAL(12, 2) NOT NULL
);
COMMENT ON TABLE order_items IS '订单明细表';
""")

vn.train(ddl="""
CREATE TABLE refunds (
    refund_id     SERIAL PRIMARY KEY,
    order_id      INT NOT NULL REFERENCES orders(order_id),
    refund_amount DECIMAL(12, 2) NOT NULL,
    refund_reason VARCHAR(200),
    refund_date   DATE NOT NULL
);
COMMENT ON TABLE refunds IS '退款表';
""")

print("  [OK] DDL 训练完成（5 张表）")

# --- 4b. 训练 Documentation（业务术语） ---
# 这对应你项目中的 schema_metadata.json -> business_terms
vn.train(documentation="销售额 = SUM(orders.total_amount) WHERE orders.status = 'delivered'")
vn.train(documentation="退款率 = COUNT(refunds.refund_id) / COUNT(orders.order_id)")
vn.train(documentation="客单价 = AVG(orders.total_amount)")
vn.train(documentation="华东区 指 customers.region = '华东' 或 orders.region = '华东'")
vn.train(documentation="活跃客户 指过去 30 天内有订单的客户")
vn.train(documentation="订单状态 cancelled 表示取消，returned 表示退货")

print("  [OK] Documentation 训练完成（6 条业务术语）")

# --- 4c. 训练 SQL 示例（最重要！） ---
# 这是 Vanna 的杀手锏：用 few-shot 示例教 LLM 正确的 SQL 写法
# 对应你项目 Prompt 中硬编码的规则（如 NULLS LAST、COALESCE 等）
vn.train(
    question="查询所有客户所在的地区",
    sql="SELECT DISTINCT region FROM customers ORDER BY region NULLS LAST",
)
vn.train(
    question="华东区有哪些客户？",
    sql="SELECT name, city FROM customers WHERE region = '华东' ORDER BY name",
)
vn.train(
    question="各区域的订单总金额是多少？",
    sql="SELECT region, COALESCE(SUM(total_amount), 0) AS total_sales FROM orders WHERE status = 'delivered' GROUP BY region ORDER BY total_sales DESC",
)
vn.train(
    question="查询电子产品类别的销售额排名",
    sql="""SELECT p.product_name, SUM(oi.subtotal) AS total_sales
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE p.category = '电子产品' AND o.status = 'delivered'
GROUP BY p.product_name
ORDER BY total_sales DESC
LIMIT 10""",
)

print("  [OK] SQL 示例训练完成（4 条 Q-SQL 对）")
print(f"\n[Chart] 训练数据总量: {vn.get_training_data().shape[0]} 条")


# ═══════════════════════════════════════════════════════════════════════
# Step 5: 提问 — 见证 Vanna 的 RAG 全流程
# ═══════════════════════════════════════════════════════════════════════
#
# ask() 内部流程（与你项目对比）：
#
# 你的项目:  intent -> schema_rag -> sql_generator -> sql_validator -> executor -> interpreter
# Vanna:     get_related_ddl() -> get_related_documentation() -> get_similar_question_sql()
#             -> get_sql_prompt() -> submit_prompt() -> extract_sql() -> run_sql()
#             -> generate_plotly_code() -> generate_followup_questions() -> generate_summary()

print("\n" + "=" * 70)
print("开始提问...")
print("=" * 70)

# 提问 1：简单查询
print("\n" + "-" * 50)
print("[?] 问题 1: 哪些区域的订单最多？")
print("-" * 50)
try:
    result = vn.ask("哪些区域的订单最多？")
    # ask() returns a tuple: (sql, df, ...) - Vanna 2.x may return 3 or 5 values
    if result:
        sql = result[0]
        df = result[1]
        print(f"\n[SQL] Generated SQL:\n{sql}")
        print(f"\n[Result]:\n{df}")
        if len(result) >= 3 and result[2] is not None:
            print(f"\n[Plotly Code]:\n{str(result[2])[:200]}...")
        if len(result) >= 5 and result[4]:
            print(f"\n[Summary]: {result[4]}")
except Exception as e:
    print(f"[ERROR]: {e}")

# Q2: Complex multi-table JOIN
print("\n" + "-" * 50)
print("[Q2] Which product categories have the highest refund rates?")
print("-" * 50)
try:
    result = vn.ask("退款率最高的产品类目是哪些？")
    if result:
        sql = result[0]
        df = result[1]
        print(f"\n[SQL] Generated SQL:\n{sql}")
        print(f"\n[Result]:\n{df}")
except Exception as e:
    print(f"[ERROR]: {e}")

# Q3: Verify RAG used training data
print("\n" + "-" * 50)
print("[Q3] Query sales in East China (should use trained doc)")
print("-" * 50)
try:
    result = vn.ask("查询华东区销售额")
    if result:
        sql = result[0]
        df = result[1]
        print(f"\n[SQL] Generated SQL:\n{sql}")
        print(f"\n[Result]:\n{df}")
except Exception as e:
    print(f"[ERROR]: {e}")


# ═══════════════════════════════════════════════════════════════════════
# Step 6: 深入 — 看看 Vanna 内部做了什么
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("[Search] 深入 Vanna 内部 — 理解 RAG 检索过程")
print("=" * 70)

# 6a. 查看检索到的相关 DDL
print("\n--- get_related_ddl('华东区销售额') ---")
related_ddl = vn.get_related_ddl("华东区销售额")
for i, item in enumerate(related_ddl):
    print(f"  [{i}] {item[:200]}...")

# 6b. 查看检索到的相关文档
print("\n--- get_related_documentation('华东区销售额') ---")
related_docs = vn.get_related_documentation("华东区销售额")
for i, item in enumerate(related_docs):
    print(f"  [{i}] {item}")

# 6c. 查看检索到的相似 Q-SQL 对
print("\n--- get_similar_question_sql('华东区销售额') ---")
similar_qs = vn.get_similar_question_sql("华东区销售额")
for i, item in enumerate(similar_qs):
    print(f"  [{i}] Q: {item['question']}")
    print(f"      SQL: {item['sql']}")

# 6d. View the assembled prompt (MOST IMPORTANT!)
# get_sql_prompt() assembles: DDL + Documentation + Few-Shot Q-SQL -> final prompt
print("\n--- get_sql_prompt (Vanna 2.x internal) ---")
# In Vanna 2.x, get_sql_prompt takes explicit params
question = "华东区销售额"
related_ddl = vn.get_related_ddl(question)
related_docs = vn.get_related_documentation(question)
similar_qs = vn.get_similar_question_sql(question)
try:
    prompt = vn.get_sql_prompt(
        initial_prompt="",
        question=question,
        question_sql_list=similar_qs,
        ddl_list=related_ddl,
        doc_list=related_docs,
    )
    print(prompt[:2000] + "\n... (truncated)")
except Exception:
    # Fallback: just show what goes into the prompt
    print(f"  DDL count: {len(related_ddl)}, Docs: {len(related_docs)}, Q-SQL pairs: {len(similar_qs)}")
    print("  (Prompt assembly happens internally in submit_prompt())")


# ═══════════════════════════════════════════════════════════════════════
# Step 7: 关键学习点
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("[Book] 对比你的项目，Vanna 值得学习的 5 个设计")
print("=" * 70)
print("""
1. 【训练数据三分法】
   Vanna 把 Schema 知识分成 DDL / Documentation / Q-SQL 三种
   你的项目目前只有 Schema RAG（表结构），缺少：
   - Documentation 的向量索引（你的是 hardcoded 在 metadata JSON 里）
   - Q-SQL 示例检索（你的 SQL 生成全靠 Prompt 规则，没有 few-shot）

2. 【检索->Prompt 全自动】
   Vanna 的 ask() 自动执行 "检索->拼 Prompt->生成->执行->解读->图表->追问"
   你的项目用 LangGraph 手动编排，更灵活但更复杂
   权衡：Vanna 一站式简单，LangGraph 适合需要自定义路由的场景

3. 【多继承组合模式】
   Vanna 用 Mixin 多继承组合"向量存储"+"LLM"+"数据库连接"
   换一个 LLM 就是换一个父类（DeepSeekChat -> OpenAI_Chat），不改核心逻辑
   你的项目用 ModelRouter 手动路由，更显式但耦合更高

4. 【SQL 示例的向量检索】
   Vanna 会把 Q-SQL 对也向量化，提问时检索最相似的
   这是你项目最大的缺失：没有 few-shot 检索机制
   效果：同样的"销售额"问题，Vanna 能检索到上次的 SQL 写法，更精准

5. 【训练数据可插拔】
   train() 可以随时追加，自动增量索引
   你的项目需要重新跑 init_db.sh 才能更新 Schema 索引
""")

print("\n[OK] Vanna 学习 Demo 完成！")
print("   打开源码阅读: site-packages/vanna/legacy/base/base.py")
print("   核心方法: train() -> get_sql_prompt() -> submit_prompt() -> run_sql()")
