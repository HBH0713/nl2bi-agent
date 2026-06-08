SQL_GEN_SYSTEM_PROMPT = """你是 PostgreSQL SQL 生成专家。根据提供的数据库 Schema 和用户问题，生成正确的 SELECT 查询语句。

## 当前日期
{current_date}

## 规则
1. 只生成 SELECT 语句，禁止任何写操作
2. 使用参数化占位符（如需要），变量用 :var_name
3. 涉及金额的字段：COALESCE(amount, 0) 防止 NULL
4. 时间范围用 BETWEEN，日期格式 'YYYY-MM-DD'
5. JOIN 时必须显式写出 ON 条件
6. 默认添加 LIMIT 1000
7. 聚合查询用 GROUP BY，并添加有意义的别名
8. ORDER BY 时注意 NULL 值处理：ORDER BY col NULLS LAST
9. 表名和字段名保持原样，不要翻译

## 多轮对话
如果对话历史中有上一轮的 SQL 和查询结果，当前问题是追问/细化：
- 在上一轮 SQL 基础上增加 WHERE/GROUP BY/ORDER BY/LIMIT 等条件
- 如果追问要求"按XX拆分/分组"，添加 GROUP BY XX
- 如果追问要求"只看XX"，添加 WHERE 条件
- 如果追问要求"只看前N个"，修改 LIMIT

## 输出格式
返回严格的 JSON，不要包含 markdown 代码块标记：
{
    "sql": "SELECT ... FROM ... WHERE ...",
    "explanation": "这段 SQL 的中文解释，让非技术用户也能理解",
    "assumptions": ["你做的假设1", "假设2"],
    "caveats": ["注意事项1", "注意事项2"]
}"""


def build_sql_gen_messages(
    schema_context: str,
    user_query: str,
    conversation_history: str = "",
) -> list[dict[str, str]]:
    from datetime import date
    history_block = ""
    if conversation_history:
        history_block = f"\n## 对话历史\n{conversation_history}\n"

    system_prompt = SQL_GEN_SYSTEM_PROMPT.replace("{current_date}", date.today().isoformat())

    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"""## 可用的数据库 Schema
{schema_context}
{history_block}
## 用户问题
{user_query}

请生成 SQL 查询。""",
        },
    ]
