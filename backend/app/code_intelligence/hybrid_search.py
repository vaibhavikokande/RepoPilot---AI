"""Hybrid search service combining lexical keyword matching and semantic vector retrieval."""

import logging
from typing import Any, Dict, List, Optional

from app.code_intelligence.models import CodeChunk
from app.code_intelligence.search import CodeSearchEngine
from app.embeddings.service import EmbeddingService
from app.vector_store.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)

# Standard Reciprocal Rank Fusion constant
RRF_K = 60


class HybridCodeSearchService:
    """Orchestrates lexical, semantic, and hybrid (RRF) search across codebase chunks."""

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[ChromaVectorStore] = None,
    ):
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or ChromaVectorStore()

    async def search(
        self,
        repo_url: str,
        query: str,
        chunks: Optional[List[CodeChunk]] = None,
        mode: str = "hybrid",
        limit: int = 10,
        entity_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute search in the requested mode ('lexical', 'semantic', or 'hybrid').

        Args:
            repo_url: Repository URL.
            query: Natural language or keyword query string.
            chunks: In-memory list of CodeChunk objects (used for lexical search and auto-indexing).
            mode: Search mode: 'lexical', 'semantic', or 'hybrid'.
            limit: Maximum result count.
            entity_types: Optional list of entity types to filter by.

        Returns:
            List of ranked result dictionaries with unified schema.
        """
        search_mode = (mode or "hybrid").lower().strip()

        if search_mode == "lexical":
            return self._search_lexical(query, chunks or [], limit, entity_types)
        elif search_mode == "semantic":
            return await self._search_semantic(repo_url, query, limit, entity_types)
        else:
            return await self._search_hybrid(repo_url, query, chunks or [], limit, entity_types)

    def _search_lexical(
        self,
        query: str,
        chunks: List[CodeChunk],
        limit: int,
        entity_types: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Run pure lexical keyword & metadata search."""
        engine = CodeSearchEngine(chunks=chunks)
        raw_results = engine.search(query=query, limit=limit, entity_types=entity_types)

        formatted: List[Dict[str, Any]] = []
        for r in raw_results:
            c: CodeChunk = r["chunk"]
            formatted.append({
                "chunk_id": c.chunk_id,
                "file_path": c.file_path,
                "entity_name": c.entity_name,
                "entity_type": c.entity_type,
                "language": c.language,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "signature": c.signature,
                "docstring": c.docstring,
                "parent": c.parent,
                "parameters": c.parameters,
                "return_type": c.return_type,
                "code_snippet": c.code_content,
                "context_header": c.context_header,
                "tokens_estimate": c.tokens_estimate,
                "score": r["score"],
                "search_mode": "lexical",
                "match_reasons": r["match_reasons"],
                "explanation": r["explanation"],
            })
        return formatted

    async def _search_semantic(
        self,
        repo_url: str,
        query: str,
        limit: int,
        entity_types: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Run pure semantic vector similarity search."""
        query_embedding = await self.embedding_service.embed_query(query)
        raw_hits = self.vector_store.search(
            repo_url=repo_url,
            query_embedding=query_embedding,
            limit=limit,
            entity_types=entity_types,
        )

        formatted: List[Dict[str, Any]] = []
        for hit in raw_hits:
            formatted.append({
                "chunk_id": hit["chunk_id"],
                "file_path": hit["file_path"],
                "entity_name": hit["entity_name"],
                "entity_type": hit["entity_type"],
                "language": hit["language"],
                "start_line": hit["start_line"],
                "end_line": hit["end_line"],
                "signature": hit["signature"],
                "docstring": hit["docstring"],
                "parent": hit["parent"],
                "parameters": [],
                "return_type": None,
                "code_snippet": hit["code_snippet"],
                "context_header": hit["context_header"],
                "tokens_estimate": hit["tokens_estimate"],
                "score": hit["similarity_score"],
                "search_mode": "semantic",
                "match_reasons": [
                    f"Semantic similarity: {hit['similarity_score']:.2f}",
                    f"Embedding cosine distance: {hit['distance']:.3f}",
                ],
                "explanation": (
                    f"{hit['entity_type'].title()} '{hit['entity_name']}' in {hit['file_path']} "
                    f"semantically aligns with query (similarity {hit['similarity_score']:.2f})."
                ),
            })
        return formatted

    async def _search_hybrid(
        self,
        repo_url: str,
        query: str,
        chunks: List[CodeChunk],
        limit: int,
        entity_types: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """Combine lexical and semantic retrieval using Reciprocal Rank Fusion (RRF)."""
        # Fetch candidate pools from both methods (up to 2x limit for better recall before fusion)
        candidate_k = max(20, limit * 2)

        lexical_hits = self._search_lexical(query, chunks, limit=candidate_k, entity_types=entity_types)
        semantic_hits = await self._search_semantic(repo_url, query, limit=candidate_k, entity_types=entity_types)

        # If one source returned no hits, return the other directly
        if not lexical_hits and not semantic_hits:
            return []
        if not lexical_hits:
            for h in semantic_hits[:limit]:
                h["search_mode"] = "hybrid (semantic-only)"
            return semantic_hits[:limit]
        if not semantic_hits:
            for h in lexical_hits[:limit]:
                h["search_mode"] = "hybrid (lexical-only)"
            return lexical_hits[:limit]

        # Map chunk_id to best item metadata
        merged_items: Dict[str, Dict[str, Any]] = {}
        rrf_scores: Dict[str, float] = {}

        # 1. Score lexical ranks: rank is 1-indexed
        for rank, item in enumerate(lexical_hits, start=1):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (0.5 / (RRF_K + rank))
            merged_items[cid] = item

        # 2. Score semantic ranks: rank is 1-indexed
        for rank, item in enumerate(semantic_hits, start=1):
            cid = item["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (0.5 / (RRF_K + rank))
            if cid not in merged_items:
                merged_items[cid] = item
            else:
                # Merge match reasons and explanations from both
                existing = merged_items[cid]
                existing["match_reasons"].extend(item["match_reasons"])
                existing["explanation"] = (
                    f"{existing['explanation']} Also matches semantically "
                    f"(similarity {item['score']:.2f})."
                )

        # 3. Sort by combined RRF score descending
        sorted_cids = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)

        results: List[Dict[str, Any]] = []
        for cid in sorted_cids[:limit]:
            item = merged_items[cid]
            item["score"] = round(rrf_scores[cid], 5)
            item["search_mode"] = "hybrid"
            results.append(item)

        return results
