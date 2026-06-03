import chromadb
from chromadb.config import Settings as ChromaSettings
from src.config import get_settings


_chroma_client = None


def get_chroma_client() -> chromadb.Client:
    global _chroma_client
    if _chroma_client is None:
        settings = get_settings()
        _chroma_client = chromadb.Client(
            ChromaSettings(
                persist_directory=settings.chroma_persist_dir,
                anonymized_telemetry=False,
            )
        )
    return _chroma_client


def get_or_create_collection(name: str = "schema_embeddings") -> chromadb.Collection:
    client = get_chroma_client()
    try:
        return client.get_collection(name)
    except Exception:
        return client.create_collection(
            name=name,
            metadata={"description": "Database schema embeddings for NL2BI RAG"},
        )


def reset_chroma() -> None:
    """重置 ChromaDB（开发调试用）"""
    global _chroma_client
    try:
        client = get_chroma_client()
        client.delete_collection("schema_embeddings")
    except Exception:
        pass
    _chroma_client = None
