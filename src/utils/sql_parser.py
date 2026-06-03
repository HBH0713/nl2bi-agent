from dataclasses import dataclass, field
from typing import Optional
import sqlglot
from sqlglot.errors import ParseError


BLOCKED_KEYWORDS = [
    "DELETE", "DROP", "TRUNCATE", "ALTER", "CREATE",
    "INSERT", "UPDATE", "GRANT", "REVOKE", "COPY",
]

DANGEROUS_FUNCTIONS = [
    "pg_sleep", "pg_read_file", "pg_write_file",
    "lo_import", "lo_export", "pg_read_binary_file",
]


@dataclass
class SQLValidationResult:
    is_valid: bool
    risk_level: str  # "safe" | "warning" | "blocked"
    error_message: Optional[str] = None
    parsed_ast: Optional[object] = None
    warnings: list = field(default_factory=list)


def validate_sql(sql: str) -> SQLValidationResult:
    """三层校验入口：先语法，再规则"""
    warnings = []

    # L1: 语法解析
    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
    except ParseError as e:
        return SQLValidationResult(
            is_valid=False,
            risk_level="blocked",
            error_message=f"SQL 语法错误: {e}",
        )

    # L2: 安全规则
    sql_upper = sql.upper()

    for keyword in BLOCKED_KEYWORDS:
        if keyword in sql_upper:
            return SQLValidationResult(
                is_valid=False,
                risk_level="blocked",
                error_message=f"不允许的操作: {keyword}。本系统仅支持 SELECT 查询。",
            )

    for func in DANGEROUS_FUNCTIONS:
        if func.upper() in sql_upper:
            return SQLValidationResult(
                is_valid=False,
                risk_level="blocked",
                error_message=f"检测到危险函数调用: {func}",
            )

    # 子查询嵌套检查
    subquery_count = sql_upper.count("SELECT") - 1
    if subquery_count > 3:
        warnings.append(f"子查询嵌套 {subquery_count} 层，可能导致性能问题")

    if "LIMIT" not in sql_upper:
        warnings.append("建议添加 LIMIT 限制返回行数")

    risk = "warning" if warnings else "safe"

    return SQLValidationResult(
        is_valid=True,
        risk_level=risk,
        parsed_ast=parsed,
        warnings=warnings,
    )


def get_table_names(sql: str) -> list[str]:
    """从 SQL 中提取表名"""
    try:
        parsed = sqlglot.parse_one(sql, read="postgres")
        return [t.name for t in parsed.find_all(sqlglot.exp.Table) if t.name]
    except ParseError:
        return []


def format_sql(sql: str) -> str:
    """格式化 SQL"""
    try:
        return sqlglot.transpile(sql, read="postgres", pretty=True)[0]
    except ParseError:
        return sql
