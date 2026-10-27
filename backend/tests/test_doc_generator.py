"""Comprehensive unit and integration tests for Day 13 AI Documentation Generator."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.doc_generator.context_collector import ContextCollector
from app.doc_generator.generator import DocGenerator
from app.doc_generator.models import (
    DocAudience,
    DocDetailLevel,
    DocGenerateRequest,
    DocGenerateResponse,
    DocTargetNotFoundError,
    DocType,
    DocValidationError,
)
from app.doc_generator.store import DocumentStore, document_store
from app.doc_generator.validator import DocValidator
from app.main import app
from app.rag.generator import BaseLLMGenerator, LLMGenerationError, MockLLMGenerator
from app.schemas.repository import RepositoryInfo


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a temporary repository workspace with manifests, code, and routes."""
    # 1. Manifest
    (tmp_path / "requirements.txt").write_text(
        "fastapi>=0.100.0\nuvicorn>=0.22.0\npydantic>=2.0\npytest>=7.0\n",
        encoding="utf-8",
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")

    # 2. Source code with routes and symbols
    app_dir = tmp_path / "app"
    app_dir.mkdir(parents=True, exist_ok=True)

    main_py = app_dir / "main.py"
    main_py.write_text(
        '"""Main API application."""\n'
        "import os\n"
        "from fastapi import FastAPI, APIRouter\n\n"
        'app = FastAPI(title="SampleService")\n'
        "router = APIRouter()\n\n"
        'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")\n'
        'SECRET_KEY = os.environ.get("APP_SECRET_KEY", "default-key")\n\n'
        '@router.get("/health")\n'
        "def health_check():\n"
        '    """Return service health status."""\n'
        '    return {"status": "ok"}\n\n'
        '@router.post("/users")\n'
        "def create_user(name: str):\n"
        '    """Create a new user account."""\n'
        '    return {"name": name}\n\n'
        "class Calculator:\n"
        '    """Utility calculator class."""\n'
        "    def add(self, a: int, b: int) -> int:\n"
        '        """Add two integers."""\n'
        "        return a + b\n",
        encoding="utf-8",
    )

    # 3. Existing Readme
    (tmp_path / "README.md").write_text(
        "# SampleService\n\nA sample application for testing.\n",
        encoding="utf-8",
    )

    # 4. Tests directory
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_main.py").write_text(
        "def test_dummy():\n    assert True\n",
        encoding="utf-8",
    )

    return tmp_path


# ==============================================================================
# 1. Context Collector Tests
# ==============================================================================

class TestContextCollector:
    """Test repository evidence gathering, manifests, routes, and AST symbols."""

    def test_collect_manifests_and_existing_docs(self, sample_repo: Path):
        collector = ContextCollector()
        context = collector.collect_context(sample_repo, DocType.README)

        assert "requirements.txt" in context.manifest_files
        assert "fastapi" in context.manifest_files["requirements.txt"]
        assert "README.md" in context.existing_docs
        assert "SampleService" in context.existing_docs["README.md"]
        assert "app/" in context.file_tree_summary
        assert "requirements.txt" in context.source_files_used

    def test_discover_api_routes(self, sample_repo: Path):
        collector = ContextCollector()
        context = collector.collect_context(sample_repo, DocType.API_REFERENCE)

        assert len(context.discovered_routes) >= 2
        route_paths = [r.path for r in context.discovered_routes]
        assert "/health" in route_paths
        assert "/users" in route_paths

        health_route = next(r for r in context.discovered_routes if r.path == "/health")
        assert health_route.method == "GET"
        assert health_route.handler_name == "health_check"

    def test_discover_symbols_and_env_vars(self, sample_repo: Path):
        collector = ContextCollector()
        context = collector.collect_context(sample_repo, DocType.FUNCTION_REFERENCE)

        symbol_names = [s.name for s in context.discovered_symbols]
        assert "health_check" in symbol_names
        assert "Calculator" in symbol_names
        assert "Calculator.add" in symbol_names

        assert "DATABASE_URL" in context.environment_vars
        assert "pytest" in context.test_frameworks

    def test_target_path_validation_and_safety(self, sample_repo: Path):
        collector = ContextCollector()

        # Valid target
        resolved = collector.validate_and_resolve_path(sample_repo, "app/main.py")
        assert resolved.exists()

        # Path traversal rejected
        with pytest.raises(DocValidationError, match="escapes repository boundary"):
            collector.validate_and_resolve_path(sample_repo, "../../etc/passwd")

        # Non-existent target
        with pytest.raises(DocTargetNotFoundError, match="not found in repository"):
            collector.validate_and_resolve_path(sample_repo, "nonexistent/file.py")


# ==============================================================================
# 2. Validator and Markdown Parser Tests
# ==============================================================================

class TestDocValidator:
    """Test Markdown section parsing, secret redaction, and unverified item checks."""

    def test_secret_redaction(self):
        validator = DocValidator()
        dirty = "OpenAI key sk-1234567890abcdef1234567890 and token ghp_1234567890abcdef1234567890"
        clean = validator.redact_secrets(dirty)
        assert "sk-1234567890abcdef1234567890" not in clean
        assert "[REDACTED_API_KEY]" in clean
        assert "ghp_1234567890abcdef1234567890" not in clean
        assert "[REDACTED_GITHUB_TOKEN]" in clean

    def test_parse_title_and_sections(self):
        validator = DocValidator()
        md = (
            "# My Custom Project\n\n"
            "This is the executive summary paragraph describing the project.\n\n"
            "## Architecture\n\n"
            "Architecture content goes here.\n\n"
            "## Installation\n\n"
            "Run pip install.\n"
        )
        title, summary, sections = validator.parse_title_and_sections(md)
        assert title == "My Custom Project"
        assert "executive summary" in summary
        assert len(sections) == 2
        assert sections[0].title == "Architecture"
        assert sections[1].title == "Installation"

    def test_unverified_items_detection(self, sample_repo: Path):
        collector = ContextCollector()
        context = collector.collect_context(sample_repo, DocType.README)
        validator = DocValidator()

        md = "## Deploy\n\nRun command `docker deploy` [Requires Confirmation: production cluster URL]\nTODO: Add tests"
        unverified, _ = validator.check_unverified_items(md, context)
        assert any("production cluster URL" in item for item in unverified)
        assert any("Add tests" in item for item in unverified)


# ==============================================================================
# 3. Doc Generator Pipeline Tests
# ==============================================================================

class TestDocGeneratorPipeline:
    """Test full generation for different document types and LLM integration."""

    @pytest.mark.anyio
    async def test_generate_readme_deterministic(self, sample_repo: Path):
        generator = DocGenerator(llm_generator=MockLLMGenerator())
        repo_info = RepositoryInfo(
            name="SampleService",
            owner="octocat",
            url="https://github.com/octocat/SampleService",
        )
        request = DocGenerateRequest(
            repository_url="https://github.com/octocat/SampleService",
            doc_type=DocType.README,
            audience=DocAudience.DEVELOPER,
            detail_level=DocDetailLevel.STANDARD,
        )

        response = await generator.generate_documentation(sample_repo, repo_info, request)

        assert response.status == "completed"
        assert response.doc_type == DocType.README
        assert "SampleService" in response.title
        assert "## Overview" in response.content
        assert "## Technology Stack" in response.content
        assert "## Repository Structure" in response.content
        assert "pip install -r requirements.txt" in response.content
        assert len(response.source_files_used) >= 2
        assert response.metadata.doc_type == "readme"

    @pytest.mark.anyio
    async def test_generate_architecture_with_mermaid(self, sample_repo: Path):
        generator = DocGenerator(llm_generator=MockLLMGenerator())
        repo_info = RepositoryInfo(
            name="SampleService",
            owner="octocat",
            url="https://github.com/octocat/SampleService",
        )
        request = DocGenerateRequest(
            repository_url="https://github.com/octocat/SampleService",
            doc_type=DocType.ARCHITECTURE,
        )

        response = await generator.generate_documentation(sample_repo, repo_info, request)

        assert response.doc_type == DocType.ARCHITECTURE
        assert "```mermaid" in response.content
        assert "graph TD" in response.content
        assert len(response.sections) >= 2

    @pytest.mark.anyio
    async def test_generate_api_reference(self, sample_repo: Path):
        generator = DocGenerator(llm_generator=MockLLMGenerator())
        repo_info = RepositoryInfo(
            name="SampleService",
            owner="octocat",
            url="https://github.com/octocat/SampleService",
        )
        request = DocGenerateRequest(
            repository_url="https://github.com/octocat/SampleService",
            doc_type=DocType.API_REFERENCE,
        )

        response = await generator.generate_documentation(sample_repo, repo_info, request)

        assert response.doc_type == DocType.API_REFERENCE
        assert "/health" in response.content
        assert "/users" in response.content
        assert "health_check" in response.content

    @pytest.mark.anyio
    async def test_generate_function_reference(self, sample_repo: Path):
        generator = DocGenerator(llm_generator=MockLLMGenerator())
        repo_info = RepositoryInfo(
            name="SampleService",
            owner="octocat",
            url="https://github.com/octocat/SampleService",
        )
        request = DocGenerateRequest(
            repository_url="https://github.com/octocat/SampleService",
            doc_type=DocType.FUNCTION_REFERENCE,
            target_symbol="Calculator",
        )

        response = await generator.generate_documentation(sample_repo, repo_info, request)

        assert response.doc_type == DocType.FUNCTION_REFERENCE
        assert "Calculator" in response.content
        assert "add" in response.content

    @pytest.mark.anyio
    async def test_generate_with_mocked_llm_response(self, sample_repo: Path):
        mock_llm = AsyncMock(spec=BaseLLMGenerator)
        mock_llm.generate.return_value = (
            "# SampleService Developer Guide\n\n"
            "This is generated by LLM.\n\n"
            "## Architecture\n\n"
            "Detailed system overview.\n"
        )

        generator = DocGenerator(llm_generator=mock_llm)
        repo_info = RepositoryInfo(
            name="SampleService",
            owner="octocat",
            url="https://github.com/octocat/SampleService",
        )
        request = DocGenerateRequest(
            repository_url="https://github.com/octocat/SampleService",
            doc_type=DocType.PROJECT_OVERVIEW,
        )

        response = await generator.generate_documentation(sample_repo, repo_info, request)

        assert response.title == "SampleService Developer Guide"
        assert len(response.sections) == 1
        assert response.sections[0].title == "Architecture"

    @pytest.mark.anyio
    async def test_llm_failure_falls_back_gracefully(self, sample_repo: Path):
        mock_llm = AsyncMock(spec=BaseLLMGenerator)
        mock_llm.generate.side_effect = LLMGenerationError("OpenAI timeout after 45s")

        generator = DocGenerator(llm_generator=mock_llm)
        repo_info = RepositoryInfo(
            name="SampleService",
            owner="octocat",
            url="https://github.com/octocat/SampleService",
        )
        request = DocGenerateRequest(
            repository_url="https://github.com/octocat/SampleService",
            doc_type=DocType.SETUP_GUIDE,
        )

        response = await generator.generate_documentation(sample_repo, repo_info, request)

        assert response.status == "completed"
        assert "Setup and Installation Guide" in response.content
        assert any("fallback" in w.lower() or "issue" in w.lower() for w in response.warnings)


# ==============================================================================
# 4. Document Store Tests
# ==============================================================================

class TestDocumentStore:
    """Test in-memory document caching and retrieval."""

    def test_save_and_retrieve(self):
        store = DocumentStore(max_capacity=5)
        repo_info = RepositoryInfo(name="test", owner="octocat", url="https://github.com/octocat/test")
        doc = DocGenerateResponse(
            document_id="doc_test123",
            repository=repo_info,
            doc_type=DocType.README,
            title="Test Doc",
            content="# Test Doc\n\nContent",
            summary="Summary",
            sections=[],
            source_files_used=["README.md"],
            missing_information=[],
            unverified_items=[],
            metadata={
                "doc_type": "readme",
                "audience": "developer",
                "detail_level": "standard",
                "model": "test-model",
                "generation_time_seconds": 0.5,
                "source_files_count": 1,
                "created_at": "2026-10-27T12:00:00Z",
            },
            status="completed",
            warnings=[],
        )

        store.save(doc)
        retrieved = store.get("doc_test123")
        assert retrieved is not None
        assert retrieved.title == "Test Doc"

        # Non-existent ID returns None
        assert store.get("doc_missing") is None


# ==============================================================================
# 5. API Endpoint Tests
# ==============================================================================

class TestDocAPIEndpoints:
    """Test POST /api/v1/repositories/generate-docs and GET /api/v1/documentation/{id}."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(app)

    def test_invalid_repository_url_rejected(self):
        payload = {
            "repository_url": "invalid-url",
            "doc_type": "readme",
        }
        res = self.client.post("/api/v1/repositories/generate-docs", json=payload)
        assert res.status_code == 400
        assert "HTTPS" in res.json()["detail"] or "Invalid" in res.json()["detail"]

    def test_path_traversal_target_rejected(self):
        payload = {
            "repository_url": "https://github.com/octocat/Hello-World",
            "doc_type": "module",
            "target_path": "../etc/passwd",
        }
        res = self.client.post("/api/v1/repositories/generate-docs", json=payload)
        assert res.status_code == 400
        assert "Path traversal" in res.json()["detail"]

    def test_successful_generate_docs_flow(self, sample_repo: Path):
        with patch("app.services.repository_service.RepositoryService.cloned_repository") as mock_clone:
            mock_clone.return_value.__enter__.return_value = (sample_repo, "main")

            payload = {
                "repository_url": "https://github.com/octocat/Hello-World",
                "doc_type": "readme",
                "audience": "developer",
                "detail_level": "standard",
            }
            res = self.client.post("/api/v1/repositories/generate-docs", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["doc_type"] == "readme"
            assert data["status"] == "completed"
            assert "SampleService" in data["title"] or "Hello-World" in data["title"]
            assert len(data["content"]) > 50

            doc_id = data["document_id"]
            # Test retrieval by ID
            get_res = self.client.get(f"/api/v1/documentation/{doc_id}")
            assert get_res.status_code == 200
            get_data = get_res.json()
            assert get_data["document_id"] == doc_id
            assert get_data["title"] == data["title"]

    def test_get_document_not_found(self):
        res = self.client.get("/api/v1/documentation/doc_nonexistent_id")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"]
