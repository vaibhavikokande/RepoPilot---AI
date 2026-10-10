"""Embeddings subsystem for RepoPilot AI."""

from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.provider import (
    LocalChromaEmbeddingProvider,
    MockEmbeddingProvider,
    OpenAIEmbeddingProvider,
    get_embedding_provider,
)
from app.embeddings.service import EmbeddingService

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingService",
    "LocalChromaEmbeddingProvider",
    "MockEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "get_embedding_provider",
]
