# 04 — SQL 安全三层校验

> 关键文件：`src/utils/sql_parser.py`（92行） + `src/agents/sql_validator.py`（56行） + `src/db/executor.py`（76行）

## 核心原则：LLM 是不可信的

> "不要相信任何来自 LLM 的输出，尤其是要直接执行的代码。"

LLM 生成的 SQL 可能包含：
- **语法错误**：幻觉字段名、错误的 JOIN 语法
- **写操作**：`INSERT`、`UPDATE`、`DELETE`、`DROP`
- **系统调用**：`pg_sleep()`、`pg_read_file()`
- **资源滥用**：无 LIMIT 的全表扫描、笛卡尔积 JOIN
- **逻辑错误**：WHERE 条件遗漏、聚合逻辑不对

本项目的三层防御体系：

```
 LLM 生成的 SQL
        │
        ▼
┌──────────────────┐
│ L1: 语法解析      │  SQLGlot 解析 AST
│    如果解析失败   │  → 直接拒绝（blocked）
└──────┬───────────┘
       │ 解析成功
        ▼
┌──────────────────┐
│ L2: 安全规则      │  黑名单关键字 + 危险函数检测
│    如果命中黑名单  │  → 直接拒绝（blocked）
└──────┬───────────┘
       │ 规则通过
        ▼
┌──────────────────┐
│ L3: 语义审查      │  Ollama 审查逻辑合理性
│    如果发现风险   │  → 标记警告（warning）
└──────┬───────────┘
       │ 通过或警告
        ▼
┌──────────────────┐
│ 数据库层兜底      │  READ ONLY + 超时 + 行数限制
│    运行时保护     │  → 硬件级别的安全兜底
└──────────────────┘
```

---

## L1：语法解析

```python
BLOCKED_KEYWORDS = [
    "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE",
    "INSERT", "UPDATE", "GRANT", "REVOKE", "COPY",
]

DANGEROUS_FUNCTIONS = [
    "pg_sleep", "pg_read_file", "pg_write_file",
    "lo_import", "lo_export", "pg_read_binary_file",
]

def validate_sql(sql: str) -> SQLValidationResult:
    # L1: SQLGlot 语法解析
    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except ParseError as e:
        return SQLValidationResult(
            is_valid=False,
            risk_level="blocked",
            error_message=f"SQL 语法错误: {e}",
        )
```

**SQLGlot** 是一个纯 Python SQL 解析器，会把 SQL 文本解析成 AST（抽象语法树）。如果解析失败 = SQL 语法有根本性错误，直接拒绝。

### 为什么用 SQLGlot 而不是正则？

```sql
-- 正则无法正确解析嵌套结构：
SELECT * FROM (SELECT id FROM (SELECT id FROM t) AS a) AS b
--                              ↑ 正则无法匹配括号配对
```

SQLGlot 能理解 SQL 的完整语法结构，包括：子查询嵌套、CTE、JOIN、窗口函数等。

---

## L2：安全规则

```python
    # 关键字黑名单
    sql_upper = sql.upper()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in sql_upper:
            return SQLValidationResult(is_valid=False, risk_level="blocked",
                error_message=f"不允许的操作: {keyword}")

    # 危险函数黑名单
    for func in DANGEROUS_FUNCTIONS:
        if func.upper() in sql_upper:
            return SQLValidationResult(is_valid=False, risk_level="blocked",
                error_message=f"检测到危险函数调用: {func}")

    # 子查询深度检查
    subquery_count = sql_upper.count("SELECT") - 1
    if subquery_count > 3:
        warnings.append(f"子查询嵌套 {subquery_count} 层，可能导致性能问题")

    # 缺少 LIMIT 警告
    if "LIMIT" not in sql_upper:
        warnings.append("建议添加 LIMIT 限制返回行数")
```

**风险分级**：

| 级别 | 含义 | 动作 |
|------|------|------|
| **blocked** | 绝对不允许 | 拒绝执行，返回错误 |
| **warning** | 有风险但可执行 | 允许执行，触发 L3 审查 |
| **safe** | 无风险 | 直接执行 |

**为什么警告 ≠ 拒绝？** 缺少 LIMIT 或子查询略深的 SQL 可能是合理的，直接拒绝会降低可用性。

---

## L3：语义审查（Ollama）

```python
async def _semantic_check(sql: str, query: str, router: ModelRouter) -> dict:
    """用 Ollama 检查 SQL 逻辑是否合理"""
    messages = [
        {"role": "system", "content": "你是 SQL 审查专家。检查 SQL 是否与用户问题匹配..."},
        {"role": "user", "content": f"用户问题: {query}\nSQL: {sql}\n请检查..."},
    ]
    response = await router.chat_json(task=ModelTask.SQL_VALIDATE, messages=messages)
    return parse_llm_json(response.content)
```

**L3 审查的维度**：
1. **表选择是否正确** — 用户问"订单金额"却查了 products 表
2. **WHERE 条件是否遗漏** — 用户问"华东区"但 SQL 没有 region 过滤
3. **聚合逻辑是否合理** — 该 GROUP BY 的字段遗漏了

**为什么 L3 用 Ollama？** 这是辅助检查，不是最终决策。Ollama 可能误判，所以结果只作为 warning 追加，不影响 SQL 是否被执行的最终判断。

---

## 数据库层兜底（最后防线）

即使前三层都被绕过，数据库层还有硬保护：

```python
async def execute_query(sql, session, timeout_s=30, max_rows=10000):
    # 1. 超时保护 — 单个查询最多执行 30 秒
    await session.execute(text(f"SET LOCAL statement_timeout = '{timeout_s}s'"))

    # 2. 只读模式 — 即使 SQL 中写了 INSERT，数据库也会拒绝
    if settings.sql_read_only:
        await session.execute(text("SET LOCAL default_transaction_read_only = on"))

    # 3. 结果截断 — 只返回前 10000 行
    result = await session.execute(text(sql))
    rows = result.fetchall()
    truncated = len(rows) >= max_rows
```

**三层数据库保护**：

| 保护措施 | 机制 | 拦截 |
|---------|------|------|
| `statement_timeout` | PostgreSQL 内置 | 慢查询、死循环 |
| `read_only = on` | PostgreSQL 内置 | INSERT/UPDATE/DELETE |
| 行数限制 | 应用层 `fetchall()` | 返回过多数据 |

---

## 安全层级总结

```
┌──────────────────────────────────────────────┐
│              安全纵深防御体系                   │
│                                               │
│  L1 语法   ←── 最容易绕过（LLM 通常语法正确）  │
│  ─────────                                   │
│  L2 规则   ←── 核心防线（拦截写操作和危险函数）│
│  ─────────                                   │
│  L3 语义   ←── 辅助审查（LLM 审查 LLM）       │
│  ─────────                                   │
│  数据库层  ←── 最终兜底（硬件级，无法绕过）    │
└──────────────────────────────────────────────┘
```

**每一层都可能被绕过，不能依赖单一防线。** 这是安全设计的基本原则。

---

## 关键学习点

1. **零信任原则**：把 LLM 视为不可信的外部输入源
2. **纵深防御**：语法 → 规则 → 语义 → 数据库，层层过滤
3. **白名单思维**：与其过滤所有危险操作（做不完），不如只允许 SELECT
4. **数据库级兜底**：应用层校验可能被绕过，数据库的 `read_only` 是硬件级别的保护
5. **风险分级而非二元判断**：`safe/warning/blocked` 三级，给予灵活性
6. **SQLGlot > 正则**：用真正的 SQL 解析器处理 SQL，而非字符串匹配

### 进阶方向

- **白名单表/字段**：允许访问的表和字段需要预先注册
- **查询审计日志**：记录所有执行的 SQL 用于事后审查（本项目用 structlog 已有基本日志）
- **数据脱敏**：对敏感字段（手机号、身份证）自动脱敏（已实现在 `src/utils/data_masker.py`）
- **查询预算**：单用户/单会话的查询次数和复杂度限制
