from urllib.parse import quote
from pydantic import field_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import logging


class Settings(BaseSettings):
    # PostgreSQL
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "bi_demo"
    pg_user: str = "bi_agent"
    pg_password: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.pg_user}:{quote(self.pg_password, safe='')}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_database}"
        )

    # DeepSeek API
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"

    # Ollama (local)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"

    # ChromaDB
    chroma_persist_dir: str = "./chroma_data"

    # History matching
    history_similarity_threshold: float = 0.85
    history_enabled: bool = True

    # Safety
    max_query_timeout_s: int = 30
    max_return_rows: int = 10000
    sql_read_only: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        level = v.upper()
        if level not in logging._nameToLevel:
            raise ValueError(f"Invalid log level: {v}. Must be one of: {list(logging._nameToLevel.keys())}")
        return level

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        fmt = v.lower()
        if fmt not in ("json", "console"):
            raise ValueError(f"Invalid log format: {v}. Must be 'json' or 'console'.")
        return fmt

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
