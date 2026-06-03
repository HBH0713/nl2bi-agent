#!/bin/bash
set -e

echo "=== NL2BI Agent 启动 ==="

# 等待 PostgreSQL 就绪
echo "[1/3] 等待数据库..."
until python -c "from src.db.connection import init_db; init_db(); print('OK')" 2>/dev/null; do
    sleep 2
done
echo "数据库就绪 ✓"

# Schema 索引（如需要）
echo "[2/3] 检查 Schema 索引..."
python scripts/index_schema.py 2>/dev/null || echo "索引已存在，跳过"

# 启动服务
echo "[3/3] 启动 API (8000) + UI (8501)..."
HF_ENDPOINT=https://hf-mirror.com python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 &
sleep 2
HF_ENDPOINT=https://hf-mirror.com streamlit run src/app.py --server.port 8501 --server.headless true &

echo "=== 就绪 ==="
echo "API: http://localhost:8000"
echo "UI:  http://localhost:8501"

# 保持前台运行
wait
