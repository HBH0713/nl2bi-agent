FROM python:3.11-slim

WORKDIR /app

# 用国内 PyPI 镜像，不需要代理
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    fastapi uvicorn[standard] \
    langgraph langchain langchain-openai langchain-ollama \
    sqlalchemy[asyncio] asyncpg \
    chromadb \
    pydantic pydantic-settings \
    sqlglot \
    structlog \
    httpx python-dotenv \
    sentence-transformers \
    streamlit plotly pandas \
    openpyxl \
    pytest pytest-asyncio pytest-cov

COPY src/ ./src/
COPY data/ ./data/
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# 预下载 BGE 中文嵌入模型
ENV HF_ENDPOINT=https://hf-mirror.com
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')" 2>/dev/null || echo "BGE download skipped"

EXPOSE 8000 8501

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
