from typing import List
from sentence_transformers import SentenceTransformer
import structlog

logger = structlog.get_logger("embedder")

MODEL_NAME = "BAAI/bge-small-zh-v1.5"


class Embedder:
    """文本向量化器，使用 BGE 中文模型"""

    def __init__(self, model_name: str = MODEL_NAME):
        import os
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        self._model = SentenceTransformer(model_name, local_files_only=False)
        self._dimension = self._model.get_sentence_embedding_dimension()
        logger.info("Embedder loaded", model=model_name, dimension=self._dimension)

    def embed(self, texts: List[str]) -> List[List[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        return self.embed([text])[0]

    @property
    def dimension(self) -> int:
        return self._dimension


_embedder: Embedder = None


def get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
