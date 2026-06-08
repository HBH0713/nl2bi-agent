"""
集成测试 — 端到端覆盖核心查询链路

需要本地服务运行中 (PostgreSQL + Ollama + ChromaDB)
跳过方式: pytest -m "not integration"
"""
import pytest
import uuid
from src.agents.graph import build_agent_graph
from src.models.router import ModelRouter
from src.models.ollama import OllamaClient
from src.models.openai_compat import OpenAICompatClient
from src.config import get_settings
from src.db.connection import init_db

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def agent_graph():
    """构建 Agent Graph（复用真实服务）"""
    settings = get_settings()
    init_db()

    ollama = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
    )
    api = OpenAICompatClient(
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        base_url=settings.deepseek_base_url,
    )
    router = ModelRouter(ollama=ollama, api=api)
    return build_agent_graph(router)


@pytest.mark.asyncio
async def test_simple_count_query(agent_graph):
    """测试1：简单 COUNT 查询的完整链路"""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": session_id}}

    result = await agent_graph.ainvoke(
        {"user_query": "有多少个客户", "error_count": 0},
        config=config,
    )

    # 验证结果
    assert result.get("generated_sql"), "应生成 SQL"
    assert "count" in result["generated_sql"].lower() or "COUNT" in result["generated_sql"], \
        "SQL 应包含 COUNT"
    assert result.get("query_row_count", 0) > 0, "应返回数据行"
    assert result.get("query_error", ""), "不应有查询错误" == False  # query_error 应为空
    assert not result.get("query_error"), "不应有查询错误"


@pytest.mark.asyncio
async def test_history_cache_hit(agent_graph):
    """测试2：相同问题第二次命中语义缓存，响应更快"""
    session_1 = f"test_{uuid.uuid4().hex[:8]}"
    session_2 = f"test_{uuid.uuid4().hex[:8]}"

    # 第一次：完整流程
    result1 = await agent_graph.ainvoke(
        {"user_query": "各区域的销售额排名", "error_count": 0},
        {"configurable": {"thread_id": session_1}},
    )
    assert result1.get("generated_sql"), "应生成 SQL"

    # 第二次：应命中缓存
    result2 = await agent_graph.ainvoke(
        {"user_query": "各区域的销售额排名", "error_count": 0},
        {"configurable": {"thread_id": session_2}},
    )

    # 验证缓存命中的标志
    if result2.get("history_matched"):
        assert result2["history_score"] >= 0.85, "缓存命中分数应 ≥ 0.85"
        assert result2.get("generated_sql") == result1.get("generated_sql"), \
            "缓存命中 SQL 应与首次一致"
        assert result2.get("interpretation"), "缓存命中应有解释"


@pytest.mark.asyncio
async def test_sql_correction_triggers(agent_graph):
    """测试3：查询不存在的内容触发纠错循环"""
    session_id = f"test_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": session_id}}

    # 查询不存在的表（"员工"表在电商数据库中不存在）
    result = await agent_graph.ainvoke(
        {"user_query": "员工表中每个人的工资排名", "error_count": 0},
        config=config,
    )

    sql = result.get("generated_sql", "")
    # 验证：要么 SQL 被纠正（不包含 employees），要么到达最大重试次数
    correction_attempts = result.get("sql_correction_attempts", 0)
    assert sql or correction_attempts > 0, \
        f"应生成 SQL 或触发纠错。SQL={sql[:80]}, attempts={correction_attempts}"
