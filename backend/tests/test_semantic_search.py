"""Tests for Semantic Search, Vector Store, Embedding Providers, and Indexing API."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.code_intelligence.hybrid_search import HybridCodeSearchService
from app.code_intelligence.models import CodeChunk
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.provider import (
    LocalChromaEmbeddingProvider,
    MockEmbeddingProvider,
    get_embedding_provider,
)
from app.embeddings.service import EmbeddingService
from app.services.repository_service import (
    RepositoryAccessError,
    RepositoryCloningError,
)
from app.vector_store.chroma_store import ChromaVectorStore, sanitize_collection_name


# ---------------------------------------------------------------------------
# Unit Tests: Embedding Providers & Service
# ---------------------------------------------------------------------------

class TestEmbeddingProviders:
    """Unit tests for embedding providers and batching service."""

    @pytest.mark.anyio
    async def test_mock_embedding_provider_properties_and_normalization(self):
        provider = MockEmbeddingProvider(dimension=64)
        assert provider.dimension == 64
        assert provider.model_name == "mock-model"

        vecs = await provider.embed_texts(["function authenticate()", "class User"])
        assert len(vecs) == 2
        assert len(vecs[0]) == 64
        assert len(vecs[1]) == 64

        # Verify unit length normalization
        norm = sum(x * x for x in vecs[0])
        assert pytest.approx(norm, rel=1e-3) == 1.0

        # Determinism check
        q_vec = await provider.embed_query("function authenticate()")
        assert vecs[0] == q_vec

    @pytest.mark.anyio
    async def test_local_chroma_embedding_provider_properties(self):
        provider = LocalChromaEmbeddingProvider()
        assert provider.dimension == 384
        assert provider.model_name == "all-MiniLM-L6-v2"

        # Verify actual embedding generation
        vec = await provider.embed_query("def add(a, b): return a + b")
        assert len(vec) == 384
        assert all(isinstance(x, float) for x in vec)

    def test_factory_get_embedding_provider(self):
        local_p = get_embedding_provider("local")
        assert isinstance(local_p, LocalChromaEmbeddingProvider)

        mock_p = get_embedding_provider("mock")
        assert isinstance(mock_p, MockEmbeddingProvider)

    @pytest.mark.anyio
    async def test_embedding_service_batching_and_chunk_formatting(self):
        mock_provider = MockEmbeddingProvider(dimension=32)
        service = EmbeddingService(provider=mock_provider, batch_size=2)

        chunk1 = CodeChunk(
            chunk_id="c1",
            file_path="auth.py",
            entity_name="login",
            entity_type="function",
            language="Python",
            start_line=1,
            end_line=5,
            signature="def login()",
            docstring="Log in user.",
            code_content="def login(): pass",
            context_header="File: auth.py | Function: login",
        )
        chunk2 = CodeChunk(
            chunk_id="c2",
            file_path="db.py",
            entity_name="connect",
            entity_type="function",
            language="Python",
            start_line=1,
            end_line=5,
            signature="def connect()",
            code_content="def connect(): pass",
            context_header="File: db.py | Function: connect",
        )
        chunk3 = CodeChunk(
            chunk_id="c3",
            file_path="config.py",
            entity_name="config",
            entity_type="file_module",
            language="Python",
            start_line=1,
            end_line=2,
            code_content="DEBUG = True",
            context_header="File: config.py | Module: config",
        )

        # Test chunk text formatting
        formatted = EmbeddingService.format_chunk_for_embedding(chunk1)
        assert "File: auth.py" in formatted
        assert "Entity: function login" in formatted
        assert "Documentation: Log in user." in formatted
        assert "def login(): pass" in formatted

        # Test batched embedding of 3 chunks with batch_size=2
        embeddings = await service.embed_chunks([chunk1, chunk2, chunk3])
        assert len(embeddings) == 3
        assert len(embeddings[0]) == 32
        assert len(embeddings[1]) == 32
        assert len(embeddings[2]) == 32


# ---------------------------------------------------------------------------
# Unit Tests: ChromaVectorStore
# ---------------------------------------------------------------------------

class TestChromaVectorStore:
    """Unit tests for persistent ChromaDB storage and similarity queries."""

    @pytest.fixture
    def test_store(self, tmp_path: Path) -> ChromaVectorStore:
        return ChromaVectorStore(persist_dir=str(tmp_path / "test_chroma"))

    def test_sanitize_collection_name(self):
        col1 = sanitize_collection_name("https://github.com/my-org/my-repo")
        col2 = sanitize_collection_name("https://github.com/my-org/my-repo/")
        assert col1 == col2
        assert col1.startswith("repo_")
        assert len(col1) <= 63

    def test_index_and_similarity_search(self, test_store: ChromaVectorStore):
        repo_url = "https://github.com/example/sample-repo"

        chunk1 = CodeChunk(
            chunk_id="auth.py#login#L1-L5",
            file_path="auth.py",
            entity_name="login",
            entity_type="function",
            language="Python",
            start_line=1,
            end_line=5,
            signature="def login(token: str)",
            docstring="Validate credentials token.",
            code_content="def login(token):\n    return verify(token)",
            context_header="File: auth.py | Function: login",
            tokens_estimate=12,
        )
        chunk2 = CodeChunk(
            chunk_id="math.py#calculate#L1-L4",
            file_path="math.py",
            entity_name="calculate",
            entity_type="function",
            language="Python",
            start_line=1,
            end_line=4,
            signature="def calculate(x: int)",
            code_content="def calculate(x):\n    return x * 2",
            context_header="File: math.py | Function: calculate",
            tokens_estimate=8,
        )

        provider = MockEmbeddingProvider(dimension=16)
        vec1 = provider._generate_vector("auth login credentials token verify")
        vec2 = provider._generate_vector("math calculate multiply double")

        # Index chunks
        res = test_store.index_chunks(
            repo_url=repo_url,
            chunks=[chunk1, chunk2],
            embeddings=[vec1, vec2],
            embedding_model="mock-model",
            dimension=16,
            force_reindex=True,
        )
        assert res["chunks_indexed"] == 2
        assert test_store.collection_exists(repo_url) is True

        # Query using a vector close to vec1
        hits = test_store.search(
            repo_url=repo_url,
            query_embedding=vec1,
            limit=5,
        )
        assert len(hits) == 2
        # Top hit must be chunk1 with highest similarity score
        assert hits[0]["entity_name"] == "login"
        assert hits[0]["similarity_score"] >= hits[1]["similarity_score"]
        assert hits[0]["start_line"] == 1
        assert hits[0]["end_line"] == 5
        assert "def login" in hits[0]["code_snippet"]

    def test_search_nonexistent_or_empty_collection(self, test_store: ChromaVectorStore):
        hits = test_store.search(
            repo_url="https://github.com/empty/repo",
            query_embedding=[0.1] * 16,
            limit=5,
        )
        assert hits == []


# ---------------------------------------------------------------------------
# Unit Tests: HybridCodeSearchService (RRF)
# ---------------------------------------------------------------------------

class TestHybridCodeSearchService:
    """Unit tests for combining lexical keyword search and semantic vector search."""

    @pytest.mark.anyio
    async def test_hybrid_search_rrf_fusion(self, tmp_path: Path):
        vector_store = ChromaVectorStore(persist_dir=str(tmp_path / "hybrid_chroma"))
        provider = MockEmbeddingProvider(dimension=16)
        embedding_service = EmbeddingService(provider=provider)

        repo_url = "https://github.com/org/hybrid-test"

        chunk_auth = CodeChunk(
            chunk_id="auth#login",
            file_path="services/auth.py",
            entity_name="login_user",
            entity_type="function",
            language="Python",
            start_line=10,
            end_line=20,
            signature="def login_user(username: str)",
            docstring="User authentication validator.",
            code_content="def login_user(username): pass",
            context_header="File: services/auth.py | Function: login_user",
        )
        chunk_db = CodeChunk(
            chunk_id="db#connect",
            file_path="db/database.py",
            entity_name="connect_db",
            entity_type="function",
            language="Python",
            start_line=1,
            end_line=5,
            signature="def connect_db()",
            code_content="def connect_db(): pass",
            context_header="File: db/database.py | Function: connect_db",
        )

        chunks = [chunk_auth, chunk_db]
        embeddings = await embedding_service.embed_chunks(chunks)

        vector_store.index_chunks(
            repo_url=repo_url,
            chunks=chunks,
            embeddings=embeddings,
            embedding_model=provider.model_name,
            dimension=provider.dimension,
            force_reindex=True,
        )

        service = HybridCodeSearchService(
            embedding_service=embedding_service,
            vector_store=vector_store,
        )

        # 1. Lexical mode
        lex_results = await service.search(
            repo_url=repo_url,
            query="login_user",
            chunks=chunks,
            mode="lexical",
            limit=5,
        )
        assert len(lex_results) >= 1
        assert lex_results[0]["search_mode"] == "lexical"
        assert lex_results[0]["entity_name"] == "login_user"

        # 2. Semantic mode
        sem_results = await service.search(
            repo_url=repo_url,
            query="validate user authentication credentials",
            chunks=chunks,
            mode="semantic",
            limit=5,
        )
        assert len(sem_results) >= 1
        assert sem_results[0]["search_mode"] == "semantic"

        # 3. Hybrid mode
        hybrid_results = await service.search(
            repo_url=repo_url,
            query="login user authentication",
            chunks=chunks,
            mode="hybrid",
            limit=5,
        )
        assert len(hybrid_results) >= 1
        assert "hybrid" in hybrid_results[0]["search_mode"]
        assert hybrid_results[0]["score"] > 0.0


# ---------------------------------------------------------------------------
# Integration Tests: Indexing & Semantic Search API Endpoints
# ---------------------------------------------------------------------------

class TestSemanticSearchAPI:
    """Integration tests for POST /api/v1/repositories/index and /semantic-search."""

    def test_index_invalid_url(self, client: TestClient):
        response = client.post(
            "/api/v1/repositories/index",
            json={"repository_url": "invalid-url"},
        )
        assert response.status_code == 400

    def test_index_successful_flow(self, client: TestClient, sample_repo_path: Path):
        @contextmanager
        def mock_cloned_repository(self, clone_url: str, owner: str, name: str):
            yield sample_repo_path, "main"

        with patch(
            "app.services.repository_service.RepositoryService.cloned_repository",
            new=mock_cloned_repository,
        ):
            response = client.post(
                "/api/v1/repositories/index",
                json={
                    "repository_url": "https://github.com/my-org/my-service",
                    "force_reindex": True,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["repository"]["name"] == "my-service"
            assert data["chunks_indexed"] >= 1
            assert data["dimension"] == 384
            assert data["total_vectors_in_index"] >= 1

    def test_semantic_search_successful_flow(
        self, client: TestClient, sample_repo_path: Path
    ):
        @contextmanager
        def mock_cloned_repository(self, clone_url: str, owner: str, name: str):
            yield sample_repo_path, "main"

        with patch(
            "app.services.repository_service.RepositoryService.cloned_repository",
            new=mock_cloned_repository,
        ):
            # 1. Semantic mode
            response = client.post(
                "/api/v1/repositories/semantic-search",
                json={
                    "repository_url": "https://github.com/my-org/my-service",
                    "query": "Where is user creation and service status defined?",
                    "limit": 5,
                    "mode": "semantic",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["search_mode"] == "semantic"
            assert len(data["results"]) >= 1

            hit = data["results"][0]
            assert "score" in hit
            assert "file_path" in hit
            assert "code_snippet" in hit
            assert "explanation" in hit

            # 2. Hybrid mode
            response_hybrid = client.post(
                "/api/v1/repositories/semantic-search",
                json={
                    "repository_url": "https://github.com/my-org/my-service",
                    "query": "create_user service status",
                    "limit": 5,
                    "mode": "hybrid",
                },
            )

            assert response_hybrid.status_code == 200
            data_hybrid = response_hybrid.json()
            assert data_hybrid["status"] == "success"
            assert "hybrid" in data_hybrid["search_mode"]
            assert len(data_hybrid["results"]) >= 1

    def test_index_repository_not_found(self, client: TestClient):
        with patch(
            "app.services.repository_service.RepositoryService.cloned_repository",
            side_effect=RepositoryAccessError("Repository does not exist"),
        ):
            response = client.post(
                "/api/v1/repositories/index",
                json={"repository_url": "https://github.com/testowner/notfound"},
            )
            assert response.status_code == 404

    def test_semantic_search_cloning_error(self, client: TestClient):
        with patch(
            "app.services.repository_service.RepositoryService.cloned_repository",
            side_effect=RepositoryCloningError("Cloning failed"),
        ):
            response = client.post(
                "/api/v1/repositories/semantic-search",
                json={
                    "repository_url": "https://github.com/testowner/fail",
                    "query": "authentication",
                },
            )
            assert response.status_code == 502
