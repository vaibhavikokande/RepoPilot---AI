"""Embedding service orchestrator managing batching, retries, and formatting."""

import asyncio
import logging
from typing import List, Optional

from app.code_intelligence.models import CodeChunk
from app.core.config import get_settings
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.provider import get_embedding_provider

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Manages text and code chunk embeddings with batching and retry logic."""

    def __init__(
        self,
        provider: Optional[BaseEmbeddingProvider] = None,
        batch_size: int = 32,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ):
        settings = get_settings()
        self.provider = provider or get_embedding_provider(
            provider_type=settings.embedding_provider,
            model_name=settings.embedding_model,
            api_key=settings.embedding_api_key or settings.openai_api_key,
        )
        self.batch_size = max(1, batch_size or settings.embedding_batch_size)
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds

    @property
    def model_name(self) -> str:
        return self.provider.model_name

    @property
    def dimension(self) -> int:
        return self.provider.dimension

    @classmethod
    def format_chunk_for_embedding(cls, chunk: CodeChunk) -> str:
        """Construct an information-rich text representation of a CodeChunk for embedding.

        Combines file location, entity type/name, scope, docstrings, and code body.
        """
        parts = [f"File: {chunk.file_path}"]
        if chunk.parent:
            parts.append(f"Scope: {chunk.parent}")
        parts.append(f"Entity: {chunk.entity_type} {chunk.entity_name}")
        if chunk.signature:
            parts.append(f"Signature: {chunk.signature}")
        if chunk.docstring:
            parts.append(f"Documentation: {chunk.docstring}")
        parts.append("Code:\n" + chunk.code_content)
        return "\n".join(parts)

    async def embed_chunks(self, chunks: List[CodeChunk]) -> List[List[float]]:
        """Format and embed a list of CodeChunks in batched requests.

        Args:
            chunks: List of CodeChunk objects.

        Returns:
            List of embedding vectors corresponding 1-to-1 with input chunks.
        """
        if not chunks:
            return []

        formatted_texts = [self.format_chunk_for_embedding(c) for c in chunks]
        return await self.embed_texts_batched(formatted_texts)

    async def embed_query(self, query: str) -> List[float]:
        """Embed a user query string with retries.

        Args:
            query: The user search query.

        Returns:
            Embedding vector of length self.dimension.
        """
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("Query string cannot be empty for embedding.")

        for attempt in range(self.max_retries):
            try:
                embedding = await self.provider.embed_query(cleaned)
                if len(embedding) != self.dimension:
                    raise ValueError(
                        f"Query embedding dimension mismatch: got {len(embedding)}, expected {self.dimension}"
                    )
                return embedding
            except Exception as exc:
                if attempt == self.max_retries - 1:
                    logger.error("Failed to embed query after %d attempts: %s", self.max_retries, exc)
                    raise
                wait_time = self.retry_delay_seconds * (2 ** attempt)
                logger.warning(
                    "Embedding query failed (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1,
                    self.max_retries,
                    exc,
                    wait_time,
                )
                await asyncio.sleep(wait_time)

    async def embed_texts_batched(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of strings dividing into manageable batches with retries.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings = await self._embed_batch_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_batch_with_retry(self, batch: List[str]) -> List[List[float]]:
        """Embed a single batch with exponential backoff on transient errors."""
        for attempt in range(self.max_retries):
            try:
                embeddings = await self.provider.embed_texts(batch)
                if len(embeddings) != len(batch):
                    raise ValueError(
                        f"Expected {len(batch)} embeddings from batch, got {len(embeddings)}"
                    )
                for vec in embeddings:
                    if len(vec) != self.dimension:
                        raise ValueError(
                            f"Vector dimension mismatch: expected {self.dimension}, got {len(vec)}"
                        )
                return embeddings
            except Exception as exc:
                if attempt == self.max_retries - 1:
                    logger.error("Batch embedding failed after %d attempts: %s", self.max_retries, exc)
                    raise
                wait_time = self.retry_delay_seconds * (2 ** attempt)
                logger.warning(
                    "Batch embedding error (attempt %d/%d): %s. Retrying in %.1fs...",
                    attempt + 1,
                    self.max_retries,
                    exc,
                    wait_time,
                )
                await asyncio.sleep(wait_time)
