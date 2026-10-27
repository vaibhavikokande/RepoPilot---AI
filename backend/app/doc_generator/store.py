"""Thread-safe in-memory store for generated technical documentation."""

import threading
from typing import Dict, List, Optional

from app.schemas.documentation import DocGenerateResponse


class DocumentStore:
    """Stores generated documents in memory for retrieval by ID."""

    def __init__(self, max_capacity: int = 100):
        self._store: Dict[str, DocGenerateResponse] = {}
        self._lock = threading.Lock()
        self._max_capacity = max_capacity
        self._keys_order: List[str] = []

    def save(self, response: DocGenerateResponse) -> None:
        """Store a generated document."""
        with self._lock:
            if response.document_id in self._store:
                self._store[response.document_id] = response
                return

            # Evict oldest if capacity exceeded
            if len(self._keys_order) >= self._max_capacity:
                oldest = self._keys_order.pop(0)
                self._store.pop(oldest, None)

            self._keys_order.append(response.document_id)
            self._store[response.document_id] = response

    def get(self, document_id: str) -> Optional[DocGenerateResponse]:
        """Retrieve a document by ID."""
        with self._lock:
            return self._store.get(document_id)

    def clear(self) -> None:
        """Clear all stored documents (primarily for test resets)."""
        with self._lock:
            self._store.clear()
            self._keys_order.clear()


# Global document store instance
document_store = DocumentStore()
