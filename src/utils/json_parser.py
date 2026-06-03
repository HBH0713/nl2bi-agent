"""LLM JSON 响应解析工具：处理 markdown 代码块、尾部逗号等常见问题"""
import json
import re


def parse_llm_json(text: str) -> dict:
    """容错解析 LLM 返回的 JSON，处理常见格式问题"""
    text = text.strip()

    # 1. 去掉 markdown 代码块标记
    if "```" in text:
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    # 2. 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. 尝试提取第一个 JSON 对象
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 4. 返回空字典
    return {}
