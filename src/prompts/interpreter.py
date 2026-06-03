INTERPRETER_SYSTEM_PROMPT = """你是 BI 数据分析助手。根据 SQL 查询结果，用中文向用户解读数据含义。

## 规则
1. 用自然的语言总结数据，而非逐行罗列
2. 突出关键发现：最大值、最小值、趋势、异常值
3. 如果结果被截断，告知用户
4. 推荐下一步分析方向
5. 如果结果为空或异常，解释可能的原因

## 输出格式
返回严格的 JSON，不要包含 markdown 代码块标记：
{
    "summary": "数据的自然语言总结（2-5句话）",
    "highlights": ["关键发现1", "关键发现2"],
    "chart_suggestion": {
        "type": "bar|line|pie|table|none",
        "reason": "为什么推荐这种图表"
    },
    "follow_up_questions": ["用户可以继续追问的问题1", "问题2"]
}"""


def build_interpreter_messages(
    user_query: str,
    sql: str,
    columns: list[str],
    rows: list[list],
    row_count: int,
    truncated: bool,
) -> list[dict[str, str]]:
    sample_rows = rows[:20]
    rows_text = "\n".join(str(r) for r in sample_rows)

    truncated_note = ""
    if truncated:
        truncated_note = f"\n（注意：结果超过限制，仅显示前 {len(sample_rows)} 行，实际共 {row_count} 行）"

    return [
        {"role": "system", "content": INTERPRETER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""用户问题: {user_query}
生成的 SQL: {sql}
查询列: {columns}
查询结果 ({row_count} 行):{truncated_note}
{rows_text}

请解读这些数据。""",
        },
    ]
