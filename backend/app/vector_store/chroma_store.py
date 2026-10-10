"""ChromaDB persistent vector store implementation for repository code chunks."""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb

from app.code_intelligence.models import CodeChunk
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def sanitize_collection_name(repo_url: str) -> str:
    """Generate a valid, deterministic ChromaDB collection name from a repository URL.

    ChromaDB collection names must be 3-63 characters and match [a-zA-Z0-9_-].
    """
    clean_url = repo_url.strip().lower().rstrip("/")
    url_hash = hashlib.sha256(clean_url.encode("utf-8")).hexdigest()[:24]
    return f"repo_{url_hash}"


class ChromaVectorStore:
    """Manages persistent ChromaDB vector collections separated by repository."""

    def __init__(self, persist_dir: Optional[str] = None):
        settings = get_settings()
        target_dir = persist_dir or settings.chroma_persist_dir

        # Ensure persist directory is resolved and exists
        path_obj = Path(target_dir)
        if not path_obj.is_absolute():
            # Place relative to backend root
            path_obj = Path(__file__).resolve().parent.parent.parent / target_dir

        path_obj.mkdir(parents=True, exist_ok=True)
        self.persist_path = path_obj

        # Initialize persistent ChromaDB client
        self.client = chromadb.PersistentClient(path=str(self.persist_path))

    def collection_exists(self, repo_url: str) -> bool:
        """Check if a vector collection exists and contains indexed chunks."""
        col_name = sanitize_collection_name(repo_url)
        try:
            col = self.client.get_collection(col_name)
            return col.count() > 0
        except Exception:
            return False

    def get_or_create_collection(
        self,
        repo_url: str,
        embedding_model: str,
        dimension: int,
        force_recreate: bool = False,
    ):
        """Retrieve or create a collection ensuring embedding model consistency."""
        col_name = sanitize_collection_name(repo_url)

        if force_recreate:
            try:
                self.client.delete_collection(col_name)
                logger.info("Deleted existing collection %s for force recreation.", col_name)
            except Exception:
                pass

        try:
            existing_col = self.client.get_collection(col_name)
            meta = existing_col.metadata or {}
            # Verify model and dimension compatibility
            existing_model = meta.get("model_name")
            existing_dim = meta.get("dimension")
            if (existing_model and existing_model != embedding_model) or (
                existing_dim and existing_dim != dimension
            ):
                logger.warning(
                    "Embedding configuration mismatch for %s (existing: %s/%s, current: %s/%s). Rebuilding collection.",
                    col_name,
                    existing_model,
                    existing_dim,
                    embedding_model,
                    dimension,
                )
                self.client.delete_collection(col_name)
                raise ValueError("Model mismatch triggered recreation")
            return existing_col
        except Exception:
            # Collection does not exist or was deleted due to mismatch
            return self.client.create_collection(
                name=col_name,
                metadata={
                    "repo_url": repo_url,
                    "model_name": embedding_model,
                    "dimension": dimension,
                    "hnsw:space": "cosine",
                },
            )

    def index_chunks(
        self,
        repo_url: str,
        chunks: List[CodeChunk],
        embeddings: List[List[float]],
        embedding_model: str,
        dimension: int,
        force_reindex: bool = False,
    ) -> Dict[str, Any]:
        """Upsert code chunks and embeddings into the repository's vector collection.

        Args:
            repo_url: Repository URL.
            chunks: List of CodeChunk instances.
            embeddings: Corresponding vector embeddings.
            embedding_model: Model name used for embeddings.
            dimension: Embedding vector dimension.
            force_reindex: Whether to clear existing vectors first.

        Returns:
            Dictionary with indexing metrics.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunk count ({len(chunks)}) does not match embedding count ({len(embeddings)})"
            )

        collection = self.get_or_create_collection(
            repo_url=repo_url,
            embedding_model=embedding_model,
            dimension=dimension,
            force_recreate=force_reindex,
        )

        if not chunks:
            return {
                "chunks_indexed": 0,
                "collection_name": collection.name,
                "total_chunks": collection.count(),
            }

        # Prepare batch arrays
        ids: List[str] = []
        docs: List[str] = []
        metas: List[Dict[str, Any]] = []
        vecs: List[List[float]] = []

        for chunk, vec in zip(chunks, embeddings):
            # ChromaDB metadata values must be primitive types (str, int, float, bool)
            metadata = {
                "repo_url": repo_url,
                "file_path": chunk.file_path,
                "entity_name": chunk.entity_name,
                "entity_type": chunk.entity_type,
                "language": chunk.language,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "signature": chunk.signature or "",
                "docstring": chunk.docstring or "",
                "parent": chunk.parent or "",
                "context_header": chunk.context_header,
                "tokens_estimate": chunk.tokens_estimate,
            }

            ids.append(chunk.chunk_id)
            docs.append(chunk.code_content)
            metas.append(metadata)
            vecs.append(vec)

        # Upsert in sub-batches of 100 to avoid request size limits
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.upsert(
                ids=ids[i : i + batch_size],
                embeddings=vecs[i : i + batch_size],
                documents=docs[i : i + batch_size],
                metadatas=metas[i : i + batch_size],
            )

        return {
            "chunks_indexed": len(chunks),
            "collection_name": collection.name,
            "total_chunks": collection.count(),
        }

    def search(
        self,
        repo_url: str,
        query_embedding: List[float],
        limit: int = 10,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search against the repository collection.

        Args:
            repo_url: Target repository URL.
            query_embedding: Vector embedding of the search query.
            limit: Maximum result count.
            entity_types: Optional list of entity types to filter by.

        Returns:
            List of result dictionaries containing metadata, code snippet, and similarity score.
        """
        col_name = sanitize_collection_name(repo_url)
        try:
            collection = self.client.get_collection(col_name)
        except Exception:
            logger.info("Collection %s for %s does not exist.", col_name, repo_url)
            return []

        total_available = collection.count()
        if total_available == 0:
            return []

        n_results = min(limit, total_available)

        where_filter = None
        if entity_types:
            clean_types = [t.lower() for t in entity_types]
            if len(clean_types) == 1:
                where_filter = {"entity_type": clean_types[0]}
            elif len(clean_types) > 1:
                where_filter = {"entity_type": {"$in": clean_types}}

        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["metadatas", "documents", "distances"],
            )
        except Exception as exc:
            logger.error("Chroma query failed on %s: %s", col_name, exc)
            return []

        hits: List[Dict[str, Any]] = []

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        ids_list = results["ids"][0]
        metas_list = results.get("metadatas", [[]])[0]
        docs_list = results.get("documents", [[]])[0]
        dists_list = results.get("distances", [[]])[0]

        for chunk_id, meta, doc, dist in zip(ids_list, metas_list, docs_list, dists_list):
            # Cosine distance in Chroma is 1 - cosine_similarity.
            # Convert cosine distance back to similarity score in [0.0, 1.0]
            similarity = round(max(0.0, min(1.0, 1.0 - float(dist))), 4)

            hits.append({
                "chunk_id": chunk_id,
                "file_path": meta.get("file_path", ""),
                "entity_name": meta.get("entity_name", ""),
                "entity_type": meta.get("entity_type", ""),
                "language": meta.get("language", ""),
                "start_line": int(meta.get("start_line", 1)),
                "end_line": int(meta.get("end_line", 1)),
                "signature": meta.get("signature") or None,
                "docstring": meta.get("docstring") or None,
                "parent": meta.get("parent") or None,
                "context_header": meta.get("context_header", ""),
                "tokens_estimate": int(meta.get("tokens_estimate", 0)),
                "code_snippet": doc,
                "similarity_score": similarity,
                "distance": round(float(dist), 4),
            })

        # Sort by similarity_score descending
        hits.sort(key=lambda x: x["similarity_score"], reverse=True)
        return hits

    def delete_index(self, repo_url: str) -> bool:
        """Delete an individual repository's vector collection."""
        col_name = sanitize_collection_name(repo_url)
        try:
            self.client.delete_collection(col_name)
            logger.info("Successfully deleted collection %s", col_name)
            return True
        except Exception as exc:
            logger.warning("Could not delete collection %s: %s", col_name, exc)
            return False

    def get_index_stats(self, repo_url: str) -> Optional[Dict[str, Any]]:
        """Get summary stats for an indexed repository."""
        col_name = sanitize_collection_name(repo_url)
        try:
            collection = self.client.get_collection(col_name)
            meta = collection.metadata or {}
            return {
                "collection_name": col_name,
                "total_chunks": collection.count(),
                "model_name": meta.get("model_name"),
                "dimension": meta.get("dimension"),
                "repo_url": meta.get("repo_url", repo_url),
            }
        except Exception:
            return None
