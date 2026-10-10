"""Tests for Code Chunking, Lexical Search Engine, and Search API."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.code_intelligence.chunker import CodeChunker
from app.code_intelligence.models import CodeChunk, CodeEntity, CodeFile
from app.code_intelligence.search import CodeSearchEngine
from app.services.repository_service import (
    RepositoryAccessError,
    RepositoryCloningError,
)


# ---------------------------------------------------------------------------
# Unit Tests: CodeChunker
# ---------------------------------------------------------------------------

class TestCodeChunker:
    """Unit tests for code chunk extraction, context headers, and token estimation."""

    def test_estimate_tokens(self):
        assert CodeChunker.estimate_tokens("") == 0
        assert CodeChunker.estimate_tokens("def hello(): pass") >= 1
        sample = "a" * 100
        assert CodeChunker.estimate_tokens(sample) == 26

    def test_build_context_header(self):
        header = CodeChunker.build_context_header(
            file_path="services/auth.py",
            entity_name="login",
            entity_type="function",
            start_line=10,
            end_line=25,
            parent=None,
            signature="def login(username: str, password: str) -> bool",
        )
        assert "File: services/auth.py" in header
        assert "Function: login" in header
        assert "Lines: 10-25" in header
        assert "Signature: def login(username: str, password: str) -> bool" in header

    def test_chunk_file_with_entities(self, tmp_path: Path):
        code = (
            "class AuthService:\n"
            '    """Authentication service."""\n'
            "    def authenticate_user(self, user: str, token: str) -> bool:\n"
            '        """Verify token."""\n'
            "        return token == 'secret'\n"
        )
        file_path = tmp_path / "auth.py"
        file_path.write_text(code, encoding="utf-8")

        entity_cls = CodeEntity(
            name="AuthService",
            type="class",
            file_path="auth.py",
            start_line=1,
            end_line=5,
            signature="class AuthService",
            docstring="Authentication service.",
        )
        entity_method = CodeEntity(
            name="authenticate_user",
            type="method",
            file_path="auth.py",
            start_line=3,
            end_line=5,
            signature="def authenticate_user(self, user: str, token: str) -> bool",
            docstring="Verify token.",
            parent="AuthService",
            parameters=["self", "user", "token"],
            return_type="bool",
        )

        code_file = CodeFile(
            path="auth.py",
            language="Python",
            size_bytes=len(code.encode("utf-8")),
            lines=5,
            entities=[entity_cls, entity_method],
        )

        chunker = CodeChunker()
        chunks = chunker.chunk_file(tmp_path, code_file)

        assert len(chunks) == 2
        cls_chunk = chunks[0]
        assert cls_chunk.entity_name == "AuthService"
        assert cls_chunk.entity_type == "class"
        assert cls_chunk.start_line == 1
        assert cls_chunk.end_line == 5
        assert "AuthService" in cls_chunk.code_content

        method_chunk = chunks[1]
        assert method_chunk.entity_name == "authenticate_user"
        assert method_chunk.entity_type == "method"
        assert method_chunk.parent == "AuthService"
        assert method_chunk.start_line == 3
        assert method_chunk.end_line == 5
        assert "return token == 'secret'" in method_chunk.code_content
        assert method_chunk.tokens_estimate > 0

    def test_chunk_file_without_entities_creates_module_chunk(self, tmp_path: Path):
        code = (
            "# Top level procedural configuration\n"
            "DEBUG = True\n"
            "DATABASE_URI = 'sqlite:///test.db'\n"
        )
        file_path = tmp_path / "config.py"
        file_path.write_text(code, encoding="utf-8")

        code_file = CodeFile(
            path="config.py",
            language="Python",
            size_bytes=len(code.encode("utf-8")),
            lines=3,
            entities=[],
        )

        chunker = CodeChunker()
        chunks = chunker.chunk_file(tmp_path, code_file)

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.entity_name == "config"
        assert chunk.entity_type == "file_module"
        assert chunk.start_line == 1
        assert chunk.end_line == 3
        assert "DATABASE_URI" in chunk.code_content


# ---------------------------------------------------------------------------
# Unit Tests: CodeSearchEngine
# ---------------------------------------------------------------------------

class TestCodeSearchEngine:
    """Unit tests for query preprocessing, tokenization, scoring, and explanation."""

    def test_split_identifier(self):
        assert CodeSearchEngine.split_identifier("UserService") == ["user", "service"]
        assert CodeSearchEngine.split_identifier("authenticate_user") == ["authenticate", "user"]
        assert CodeSearchEngine.split_identifier("JWTAuthManager") == ["jwt", "auth", "manager"]
        assert CodeSearchEngine.split_identifier("getHTTPResponse") == ["get", "http", "response"]
        assert CodeSearchEngine.split_identifier("") == []

    def test_preprocess_conversational_query(self):
        query = "Where is user authentication handled?"
        core_tokens, expanded = CodeSearchEngine.preprocess_query(query)

        # Conversational stop words ('where', 'is', 'handled') should be stripped
        assert "where" not in core_tokens
        assert "is" not in core_tokens
        assert "handled" not in core_tokens

        # Core terms preserved
        assert "user" in core_tokens
        assert "authentication" in core_tokens

        # Expanded synonym terms
        assert "auth" in expanded
        assert "login" in expanded

    def test_search_scoring_and_ranking(self):
        c1 = CodeChunk(
            chunk_id="c1",
            file_path="services/auth_service.py",
            entity_name="authenticate_user",
            entity_type="method",
            language="Python",
            start_line=10,
            end_line=20,
            signature="def authenticate_user(username: str, token: str) -> bool",
            docstring="Authenticate user credentials against auth database.",
            parent="AuthService",
            parameters=["username", "token"],
            return_type="bool",
            code_content="def authenticate_user(username, token):\n    return verify(token)",
            context_header="File: services/auth_service.py | Method: authenticate_user",
            tokens_estimate=15,
        )
        c2 = CodeChunk(
            chunk_id="c2",
            file_path="utils/helpers.py",
            entity_name="format_date",
            entity_type="function",
            language="Python",
            start_line=1,
            end_line=5,
            signature="def format_date(d: str) -> str",
            docstring="Format date string.",
            parent=None,
            parameters=["d"],
            return_type="str",
            code_content="def format_date(d):\n    return str(d)",
            context_header="File: utils/helpers.py | Function: format_date",
            tokens_estimate=10,
        )

        engine = CodeSearchEngine(chunks=[c1, c2])
        results = engine.search("Where is user authentication handled?")

        assert len(results) == 1
        best = results[0]
        assert best["chunk"].entity_name == "authenticate_user"
        assert best["score"] > 10.0
        assert "authenticate_user" in best["explanation"]
        assert any("auth" in r.lower() or "user" in r.lower() for r in best["match_reasons"])

    def test_search_filtering_by_entity_type(self):
        c_fn = CodeChunk(
            chunk_id="fn1",
            file_path="auth.py",
            entity_name="login",
            entity_type="function",
            language="Python",
            start_line=1,
            end_line=5,
            signature="def login()",
            code_content="def login(): pass",
            context_header="Function: login",
        )
        c_cls = CodeChunk(
            chunk_id="cls1",
            file_path="auth.py",
            entity_name="LoginManager",
            entity_type="class",
            language="Python",
            start_line=10,
            end_line=20,
            signature="class LoginManager",
            code_content="class LoginManager: pass",
            context_header="Class: LoginManager",
        )

        engine = CodeSearchEngine(chunks=[c_fn, c_cls])

        # Filter only classes
        results_class = engine.search("login", entity_types=["class"])
        assert len(results_class) == 1
        assert results_class[0]["chunk"].entity_name == "LoginManager"

        # Filter only functions
        results_fn = engine.search("login", entity_types=["function"])
        assert len(results_fn) == 1
        assert results_fn[0]["chunk"].entity_name == "login"

    def test_search_empty_query(self):
        engine = CodeSearchEngine(chunks=[])
        assert engine.search("") == []
        assert engine.search("   ") == []


# ---------------------------------------------------------------------------
# Integration Tests: Search API Endpoint
# ---------------------------------------------------------------------------

class TestCodeSearchAPI:
    """Integration tests for POST /api/v1/repositories/search-code."""

    def test_search_invalid_url(self, client: TestClient):
        response = client.post(
            "/api/v1/repositories/search-code",
            json={"repository_url": "invalid-url", "query": "auth"},
        )
        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"] or "Only secure HTTPS" in response.json()["detail"]

    def test_search_non_github_url(self, client: TestClient):
        response = client.post(
            "/api/v1/repositories/search-code",
            json={"repository_url": "https://gitlab.com/owner/repo", "query": "auth"},
        )
        assert response.status_code == 400
        assert "Only GitHub repositories are supported" in response.json()["detail"]

    def test_search_empty_query_rejected(self, client: TestClient):
        response = client.post(
            "/api/v1/repositories/search-code",
            json={"repository_url": "https://github.com/owner/repo", "query": ""},
        )
        assert response.status_code == 422

    def test_search_successful_flow(self, client: TestClient, sample_repo_path: Path):
        @contextmanager
        def mock_cloned_repository(self, clone_url: str, owner: str, name: str):
            yield sample_repo_path, "main"

        with patch(
            "app.services.repository_service.RepositoryService.cloned_repository",
            new=mock_cloned_repository,
        ):
            response = client.post(
                "/api/v1/repositories/search-code",
                json={
                    "repository_url": "https://github.com/my-org/my-service",
                    "query": "Where is user creation handled?",
                    "limit": 5,
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "success"
            assert data["query"] == "Where is user creation handled?"
            assert data["repository"]["name"] == "my-service"
            assert data["total_chunks_indexed"] >= 1
            assert data["total_results"] >= 1

            top_hit = data["results"][0]
            assert "score" in top_hit
            assert top_hit["score"] > 0
            assert "explanation" in top_hit
            assert "code_snippet" in top_hit
            assert "match_reasons" in top_hit
            assert len(top_hit["match_reasons"]) > 0

    def test_search_repository_not_found(self, client: TestClient):
        with patch(
            "app.services.repository_service.RepositoryService.cloned_repository",
            side_effect=RepositoryAccessError("Repository does not exist"),
        ):
            response = client.post(
                "/api/v1/repositories/search-code",
                json={
                    "repository_url": "https://github.com/testowner/notfound",
                    "query": "database connection",
                },
            )
            assert response.status_code == 404
            assert "does not exist" in response.json()["detail"]

    def test_search_repository_cloning_error(self, client: TestClient):
        with patch(
            "app.services.repository_service.RepositoryService.cloned_repository",
            side_effect=RepositoryCloningError("Failed to clone"),
        ):
            response = client.post(
                "/api/v1/repositories/search-code",
                json={
                    "repository_url": "https://github.com/testowner/fail",
                    "query": "database connection",
                },
            )
            assert response.status_code == 502
            assert "Failed to clone" in response.json()["detail"]
