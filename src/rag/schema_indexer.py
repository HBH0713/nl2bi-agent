import json
from typing import List, Dict
from src.rag.embedder import get_embedder
from src.db.chroma_client import get_or_create_collection, reset_chroma
import structlog

logger = structlog.get_logger("schema_indexer")


def build_schema_texts(metadata_path: str = "data/schema_metadata.json") -> List[Dict]:
    """从 metadata JSON 构建三类 embedding 文本"""
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    documents = []

    # 1. 表级别
    for table in metadata["tables"]:
        col_descs = ", ".join(
            f"{c['name']}({c['description']})" for c in table["columns"]
        )
        text = (
            f"表 {table['table_name']}: {table['description']}。"
            f"字段包括: {col_descs}。"
            f"大约 {table.get('row_count_estimate', '未知')} 行数据。"
        )
        documents.append({
            "id": f"table_{table['table_name']}",
            "text": text,
            "type": "table",
            "table_name": table["table_name"],
            "metadata": {
                "type": "table",
                "table_name": table["table_name"],
                "row_count": table.get("row_count_estimate", 0),
            }
        })

    # 2. 字段级别
    for table in metadata["tables"]:
        for col in table["columns"]:
            samples = col.get("sample_values", [])
            samples_str = f" 示例值: {samples}" if samples else ""
            text = (
                f"字段 {table['table_name']}.{col['name']}: {col['description']}，"
                f"类型 {col['type']}。{samples_str}"
            )
            documents.append({
                "id": f"col_{table['table_name']}_{col['name']}",
                "text": text,
                "type": "column",
                "table_name": table["table_name"],
                "column_name": col["name"],
                "metadata": {
                    "type": "column",
                    "table_name": table["table_name"],
                    "column_name": col["name"],
                }
            })

    # 3. 业务概念级别
    for term in metadata.get("business_terms", []):
        text = f"业务术语「{term['term']}」: {term['description']}。SQL 写法: {term.get('sql_fragment', '')}"
        documents.append({
            "id": f"term_{term['term']}",
            "text": text,
            "type": "business_term",
            "term": term["term"],
            "metadata": {
                "type": "business_term",
                "term": term["term"],
                "sql_fragment": term.get("sql_fragment", ""),
            }
        })

    return documents


def index_schemas(metadata_path: str = "data/schema_metadata.json", reset: bool = False) -> int:
    """将 Schema 元数据向量化并存入 ChromaDB"""
    if reset:
        reset_chroma()

    embedder = get_embedder()
    collection = get_or_create_collection("schema_embeddings")

    documents = build_schema_texts(metadata_path)

    if not documents:
        logger.warning("No schema documents to index")
        return 0

    texts = [d["text"] for d in documents]
    embeddings = embedder.embed(texts)
    ids = [d["id"] for d in documents]
    metadatas = [d["metadata"] for d in documents]

    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch_end = min(i + batch_size, len(documents))
        collection.add(
            ids=ids[i:batch_end],
            embeddings=embeddings[i:batch_end],
            metadatas=metadatas[i:batch_end],
            documents=texts[i:batch_end],
        )

    logger.info("Schema indexing complete", total_documents=len(documents))
    return len(documents)
