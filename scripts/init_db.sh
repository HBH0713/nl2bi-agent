#!/bin/bash
set -e

echo "=== NL2BI Agent 环境初始化 ==="

echo "[1/5] 启动 PostgreSQL + Ollama + ChromaDB..."
docker compose up -d postgres ollama chromadb

echo "[2/5] 等待 PostgreSQL 就绪..."
until docker compose exec -T postgres pg_isready -U bi_agent -d bi_demo > /dev/null 2>&1; do
    sleep 2
done
echo "PostgreSQL 就绪 ✓"

echo "[3/5] 生成测试数据（约 5 万订单）..."
python scripts/seed_data.py
echo "测试数据生成完成 ✓"

echo "[4/5] 拉取 Qwen 2.5 模型..."
docker compose exec -T ollama ollama pull qwen2.5:7b
echo "Ollama 模型就绪 ✓"

echo "[5/5] Schema 向量化入库..."
python scripts/index_schema.py
echo "Schema 向量化完成 ✓"

echo "=== 初始化完成！==="
echo "启动 API 服务: docker compose up -d api"
echo "或本地启动: uvicorn src.main:app --reload"
