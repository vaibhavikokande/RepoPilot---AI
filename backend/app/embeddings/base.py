"""Base abstract interface for embedding providers."""

from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddingProvider(ABC):
    """Abstract base class defining the provider-independent embedding interface."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Name or identifier of the underlying embedding model."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Expected vector dimension produced by this model."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of input texts.

        Args:
            texts: List of strings to embed.

        Returns:
            List of vector embeddings, each of length self.dimension.
        """
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Generate a single vector embedding for a search query.

        Args:
            query: The user search query string.

        Returns:
            Vector embedding of length self.dimension.
        """
        pass
