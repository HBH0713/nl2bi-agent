"""周报生成 Agent — 将报表请求拆解为多个子查询"""
import json
from src.agents.state import AgentState
from src.models.router import ModelRouter, ModelTask
from src.utils.json_parser import parse_llm_json
import structlog

logger = structlog.get_logger("agent.report_planner")

REPORT_PLANNER_PROMPT = """你是 BI 报表规划专家。根据用户请求，拆解成 3-6 个可独立执行的子查询。

数据库包含：customers(客户), products(产品), orders(订单), order_items(明细), refunds(退款)
当前日期：{current_date}
⚠️ 数据库中订单数据的日期范围是 2025-01-01 到 2025-12-31。
如果用户说"本周""本月"，请替换为数据范围内的具体日期（如5月中旬、6月第一周等），或直接去掉时间过滤查全部数据。
如果查询不指定时间，默认查全部历史数据。

返回 JSON：
{
    "title": "报表标题",
    "date_range": "日期范围描述",
    "sub_queries": [
        {"question": "中文问题", "description": "这个子查询查什么"}
    ]
}"""


async def report_planner(state: AgentState, router: ModelRouter) -> dict:
    """报表规划节点 — 拆解用户请求为子查询列表"""
    from datetime import date

    query = state.get("user_query", "")

    messages = [
        {"role": "system", "content": REPORT_PLANNER_PROMPT.replace("{current_date}", date.today().isoformat())},
        {"role": "user", "content": query},
    ]

    try:
        response = await router.chat_json(task=ModelTask.INTERPRET, messages=messages, temperature=0.2)
        plan = parse_llm_json(response.content)
        sub_queries = plan.get("sub_queries", [])
        title = plan.get("title", "数据报表")

        logger.info("Report plan created", title=title, sub_queries_count=len(sub_queries))

        return {
            "interpretation": "",  # will be filled by report runner
            "report_title": title,
            "report_sub_queries": sub_queries,
            "report_date_range": plan.get("date_range", ""),
        }

    except Exception as e:
        logger.error("Report planning failed", error=str(e))
        # 默认指标
        return {
            "report_title": "运营数据概览",
            "report_sub_queries": [
                {"question": "各区域销售额排名", "description": "区域业绩对比"},
                {"question": "本周订单量按日统计", "description": "订单趋势"},
                {"question": "各产品类目销售额占比", "description": "类目分析"},
                {"question": "退款金额最高的5个产品", "description": "退款分析"},
                {"question": "客户数按渠道统计", "description": "渠道分析"},
            ],
            "report_date_range": "近7天",
        }
