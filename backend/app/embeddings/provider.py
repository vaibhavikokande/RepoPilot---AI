"""Concrete embedding providers supporting local, hosted, and mock execution."""

import hashlib
import logging
import math
from typing import List, Optional
import anyio
import httpx

from app.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)


class LocalChromaEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding provider powered by ChromaDB's ONNX all-MiniLM-L6-v2 model (384-dim)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._dimension = 384
        self._ef = None

    def _get_ef(self):
        if self._ef is None:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            self._ef = DefaultEmbeddingFunction()
        return self._ef

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _sync_embed(self, texts: List[str]) -> List[List[float]]:
        ef = self._get_ef()
        raw = ef(texts)
        # Convert numpy arrays to Python float lists if needed
        return [list(map(float, vec)) for vec in raw]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # Run CPU-bound ONNX model in thread pool to avoid blocking async event loop
        return await anyio.to_thread.run_sync(self._sync_embed, texts)

    async def embed_query(self, query: str) -> List[float]:
        results = await self.embed_texts([query])
        return results[0]


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """Hosted OpenAI embeddings provider (e.g. text-embedding-3-small)."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        dimension: int = 1536,
    ):
        if not api_key:
            raise ValueError("OpenAI API key must be provided when using OpenAIEmbeddingProvider.")
        self.api_key = api_key
        self._model_name = model_name
        self._dimension = dimension
        self.api_url = "https://api.openai.com/v1/embeddings"

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model_name,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.api_url, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenAI embedding request failed ({response.status_code}): {response.text}"
                )
            data = response.json()
            # Items in data["data"] are ordered by index
            sorted_items = sorted(data["data"], key=lambda item: item["index"])
            return [item["embedding"] for item in sorted_items]

    async def embed_query(self, query: str) -> List[float]:
        results = await self.embed_texts([query])
        return results[0]


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic, fast mock embedding provider for tests and offline development.

    Generates reproducible unit-normalized vectors using string hash digests.
    """

    def __init__(self, model_name: str = "mock-model", dimension: int = 384):
        self._model_name = model_name
        self._dimension = dimension

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    def _generate_vector(self, text: str) -> List[float]:
        """Generate a deterministic unit-normalized pseudo-embedding vector for text."""
        vec: List[float] = []
        seed = text.encode("utf-8")
        counter = 0

        while len(vec) < self._dimension:
            h = hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
            for b in h:
                # Map byte 0-255 to float -1.0 to 1.0
                vec.append((float(b) / 127.5) - 1.0)
                if len(vec) == self._dimension:
                    break
            counter += 1

        # L2-normalize vector to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_query(self, query: str) -> List[float]:
        return self._generate_vector(query)


def get_embedding_provider(
    provider_type: str,
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseEmbeddingProvider:
    """Factory creating the appropriate BaseEmbeddingProvider instance."""
    p_type = (provider_type or "local").lower().strip()

    if p_type in ("openai", "hosted"):
        return OpenAIEmbeddingProvider(
            api_key=api_key or "",
            model_name=model_name or "text-embedding-3-small",
        )
    elif p_type == "mock":
        return MockEmbeddingProvider(model_name=model_name or "mock-model")
    else:
        # Default local ONNX embedding provider
        return LocalChromaEmbeddingProvider(model_name=model_name or "all-MiniLM-L6-v2")
