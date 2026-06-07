#!/bin/bash
set -e

echo "============================================"
echo "  NL2BI Agent — Starting..."
echo "============================================"

# ── 1. Wait for PostgreSQL ──
echo "[1/3] Waiting for PostgreSQL (${PG_HOST}:${PG_PORT})..."
MAX_RETRIES=30
RETRY=0
until python -c "
from src.db.connection import init_db
init_db()
print('OK')
" 2>/dev/null; do
    RETRY=$((RETRY + 1))
    if [ $RETRY -ge $MAX_RETRIES ]; then
        echo "ERROR: PostgreSQL not ready after ${MAX_RETRIES} retries"
        exit 1
    fi
    sleep 2
done
echo "  PostgreSQL ready."

# ── 2. Schema indexing ──
echo "[2/3] Indexing schema into ChromaDB..."
python scripts/index_schema.py 2>/dev/null && echo "  Schema indexed." || echo "  Index already exists, skipped."

# ── 3. Start services ──
echo "[3/3] Starting API (:8000) + Streamlit (:8501)..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --log-level info &
sleep 2
streamlit run src/app.py --server.port 8501 --server.headless true \
    --server.enableCORS false --server.enableXsrfProtection false &

echo ""
echo "============================================"
echo "  NL2BI Agent Ready"
echo "  API:       http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo "  Streamlit: http://localhost:8501"
echo "============================================"

wait
