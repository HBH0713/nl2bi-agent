import os
from typing import List

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from src.config import get_settings


class _BGEZhEmbeddingFunction(EmbeddingFunction):
    """使用 BGE 中文模型的 ChromaDB Embedding Function"""

    def __init__(self):
        self._embedder = None

    @property
    def _model(self):
        if self._embedder is None:
            os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("BAAI/bge-small-zh-v1.5", local_files_only=False)
        return self._embedder

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self._model.encode(input, normalize_embeddings=True)
        return embeddings.tolist()


_chroma_client = None
_embed_fn = _BGEZhEmbeddingFunction()


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        from chromadb.config import Settings as ChromaSettings
        settings = get_settings()
        persist_dir = settings.chroma_persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_or_create_collection(name: str = "schema_embeddings") -> chromadb.Collection:
    client = get_chroma_client()
    try:
        return client.get_collection(name, embedding_function=_embed_fn)
    except Exception:
        return client.create_collection(
            name=name,
            metadata={"description": "Database schema embeddings for NL2BI RAG"},
            embedding_function=_embed_fn,
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
