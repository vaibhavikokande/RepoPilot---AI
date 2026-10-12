"""Retriever for querying repository code chunks for RAG."""

import logging
from typing import Any, List, Optional

from app.code_intelligence.hybrid_search import HybridCodeSearchService
from app.code_intelligence.models import CodeChunk
from app.embeddings.service import EmbeddingService
from app.rag.models import RetrievedSource
from app.vector_store.chroma_store import ChromaVectorStore

logger = logging.getLogger(__name__)


class CodeRetriever:
    """Retrieves relevant code chunks for RAG questions using hybrid vector and lexical search."""

    def __init__(
        self,
        vector_store: Optional[ChromaVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        hybrid_search_service: Optional[HybridCodeSearchService] = None,
        repo_service: Optional[Any] = None,
        analyzer: Optional[Any] = None,
        chunker: Optional[Any] = None,
    ):
        self.vector_store = vector_store or ChromaVectorStore()
        self.embedding_service = embedding_service or EmbeddingService()
        self.hybrid_search = hybrid_search_service or HybridCodeSearchService(
            embedding_service=self.embedding_service,
            vector_store=self.vector_store,
        )

        if repo_service is not None:
            self.repo_service = repo_service
        else:
            from app.services.repository_service import RepositoryService
            self.repo_service = RepositoryService()

        if analyzer is not None:
            self.analyzer = analyzer
        else:
            from app.code_intelligence.analyzer import CodeIntelligenceAnalyzer
            self.analyzer = CodeIntelligenceAnalyzer()

        if chunker is not None:
            self.chunker = chunker
        else:
            from app.code_intelligence.chunker import CodeChunker
            self.chunker = CodeChunker()

    async def retrieve(
        self,
        repo_url: str,
        question: str,
        top_k: int = 5,
        chunks: Optional[List[CodeChunk]] = None,
        clone_url: Optional[str] = None,
        owner: Optional[str] = None,
        name: Optional[str] = None,
    ) -> List[RetrievedSource]:
        """Retrieve the top-k most relevant code chunks and format them into RetrievedSource objects.

        Args:
            repo_url: Repository URL.
            question: User's question.
            top_k: Number of chunks to retrieve.
            chunks: Optional pre-loaded CodeChunk instances.
            clone_url: Optional clone URL if repository needs indexing.
            owner: Optional repo owner.
            name: Optional repo name.

        Returns:
            List of RetrievedSource instances labeled with deterministic S1, S2, ... IDs.
        """
        # 1. Check if vector index exists
        index_exists = self.vector_store.collection_exists(repo_url)

        # 2. If index doesn't exist and clone info is available, build the index on demand
        if not index_exists and clone_url and owner and name:
            logger.info("Vector index not found for %s. Indexing repository on demand...", repo_url)
            with self.repo_service.cloned_repository(
                clone_url=clone_url,
                owner=owner,
                name=name,
            ) as (repo_path, _):
                _, files, _, _, _, _ = self.analyzer.analyze_repository(repo_path)
                chunks = self.chunker.chunk_repository(repo_path=repo_path, code_files=files)

                if chunks:
                    embeddings = await self.embedding_service.embed_chunks(chunks)
                    self.vector_store.index_chunks(
                        repo_url=repo_url,
                        chunks=chunks,
                        embeddings=embeddings,
                        embedding_model=self.embedding_service.model_name,
                        dimension=self.embedding_service.dimension,
                    )
                    logger.info("Successfully indexed %d chunks for %s.", len(chunks), repo_url)

        # 3. Execute search via HybridCodeSearchService
        mode = "hybrid" if chunks else "semantic"
        raw_hits = await self.hybrid_search.search(
            repo_url=repo_url,
            query=question,
            chunks=chunks,
            mode=mode,
            limit=top_k * 2,  # Fetch slightly more to deduplicate
        )

        if not raw_hits and not index_exists and chunks:
            # If collection was never saved (e.g. unit tests without ChromaDB persistence), run lexical search directly
            from app.code_intelligence.search import CodeSearchEngine
            engine = CodeSearchEngine(chunks=chunks)
            lexical_results = engine.search(query=question, limit=top_k)
            raw_hits = [
                {
                    "chunk_id": r["chunk"].chunk_id,
                    "file_path": r["chunk"].file_path,
                    "entity_name": r["chunk"].entity_name,
                    "entity_type": r["chunk"].entity_type,
                    "language": r["chunk"].language,
                    "start_line": r["chunk"].start_line,
                    "end_line": r["chunk"].end_line,
                    "signature": r["chunk"].signature,
                    "docstring": r["chunk"].docstring,
                    "parent": r["chunk"].parent,
                    "code_snippet": r["chunk"].code_content,
                    "context_header": r["chunk"].context_header,
                    "tokens_estimate": r["chunk"].tokens_estimate,
                    "score": r["score"],
                }
                for r in lexical_results
            ]

        # 4. Deduplicate hits by (file_path, start_line, end_line)
        seen_keys = set()
        deduped_hits = []

        for hit in raw_hits:
            key = (hit.get("file_path"), hit.get("start_line"), hit.get("end_line"))
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_hits.append(hit)
            if len(deduped_hits) >= top_k:
                break

        # 5. Format into RetrievedSource models with deterministic S1, S2, ... IDs
        retrieved_sources: List[RetrievedSource] = []
        for i, hit in enumerate(deduped_hits):
            source_id = f"S{i + 1}"
            source = RetrievedSource(
                source_id=source_id,
                chunk_id=hit.get("chunk_id", f"chunk_{i}"),
                file_path=hit.get("file_path", ""),
                start_line=int(hit.get("start_line", 1)),
                end_line=int(hit.get("end_line", 1)),
                entity_name=hit.get("entity_name", ""),
                entity_type=hit.get("entity_type", "code"),
                language=hit.get("language", "text"),
                signature=hit.get("signature"),
                docstring=hit.get("docstring"),
                code_content=hit.get("code_snippet", ""),
                score=round(float(hit.get("score", 0.0)), 4),
            )
            retrieved_sources.append(source)

        return retrieved_sources
