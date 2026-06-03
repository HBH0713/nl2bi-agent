import pytest
import sys
sys.path.insert(0, ".")

from src.config import Settings


@pytest.fixture
def test_settings():
    return Settings(
        pg_host="localhost",
        pg_port=5432,
        pg_database="bi_demo",
        pg_user="bi_agent",
        pg_password="changeme",
        deepseek_api_key="test-key",
        ollama_base_url="http://localhost:11434",
        ollama_model="qwen2.5:7b",
    )
