"""将 schema_metadata.json 向量化存入 ChromaDB"""
import sys
sys.path.insert(0, ".")

from src.rag.schema_indexer import index_schemas

if __name__ == "__main__":
    count = index_schemas("data/schema_metadata.json", reset=True)
    print(f"Indexed {count} schema documents into ChromaDB")
