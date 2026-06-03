FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]" openpyxl streamlit plotly pandas

# 复制源码
COPY src/ ./src/
COPY data/ ./data/
COPY scripts/ ./scripts/

# 预下载 BGE 模型（构建时缓存）
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-zh-v1.5')" || true

EXPOSE 8000 8501

# 启动脚本
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
