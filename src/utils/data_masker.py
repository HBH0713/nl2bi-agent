"""数据脱敏：自动检测并脱敏敏感字段"""
import re

# 敏感字段关键词（中文 + 英文）
SENSITIVE_PATTERNS = {
    "name": "姓名",
    "phone": "电话",
    "email": "邮箱",
    "address": "地址",
    "id_card": "身份证",
    "password": "密码",
    "salary": "薪资",
    "bank": "银行卡",
}


def _mask_name(value: str) -> str:
    """张三 → 张*"""
    if len(value) <= 1:
        return "*"
    return value[0] + "*" * (len(value) - 1)


def _mask_phone(value: str) -> str:
    """13812345678 → 138****5678"""
    s = str(value)
    if len(s) >= 7:
        return s[:3] + "****" + s[-4:]
    return "****"


def _mask_email(value: str) -> str:
    """test@example.com → t***@example.com"""
    s = str(value)
    if "@" in s:
        local, domain = s.split("@", 1)
        return local[0] + "***@" + domain
    return "***"


def _mask_default(value: str) -> str:
    s = str(value)
    if len(s) <= 3:
        return s[0] + "*" * (len(s) - 1) if len(s) > 1 else "*"
    return s[:2] + "***" + s[-2:]


def is_sensitive_column(col_name: str) -> str | None:
    """判断列名是否为敏感字段，返回敏感类型"""
    col_lower = col_name.lower().replace("_", "")
    for key, label in SENSITIVE_PATTERNS.items():
        if key in col_lower:
            return label
    return None


def mask_value(col_name: str, value) -> str:
    """对单个值脱敏"""
    s = str(value)
    col_lower = col_name.lower()

    if "phone" in col_lower or "tel" in col_lower or "手机" in col_lower:
        return _mask_phone(s)
    if "email" in col_lower or "邮箱" in col_lower:
        return _mask_email(s)
    if "name" in col_lower or "姓名" in col_lower or "客户" in col_lower:
        return _mask_name(s)
    return _mask_default(s)


def mask_dataframe(df, sensitive_cols: list[str]) -> dict:
    """对 DataFrame 中的敏感列脱敏，返回脱敏后的数据 + 脱敏报告"""
    masked_rows = []
    report = {}

    for col in sensitive_cols:
        if col in df.columns:
            report[col] = is_sensitive_column(col) or "敏感字段"

    if not report:
        return {"rows": df.values.tolist(), "masked": []}

    for _, row in df.iterrows():
        new_row = list(row)
        for col in sensitive_cols:
            if col in df.columns:
                idx = df.columns.get_loc(col)
                new_row[idx] = mask_value(col, row[col])
        masked_rows.append(new_row)

    return {"rows": masked_rows, "masked": list(report.keys())}
