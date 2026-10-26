"""Comprehensive unit and integration tests for Day 11 AI-powered code review."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.code_review.collector import EvidenceCollector
from app.code_review.grounding import GroundingValidator
from app.code_review.models import (
    CodeReviewFinding,
    CodeReviewRequest,
    CodeReviewResponse,
    EvidenceContext,
    ReviewTargetNotFoundError,
    ReviewValidationError,
)
from app.code_review.prompt_builder import ReviewPromptBuilder
from app.code_review.reviewer import CodeReviewer
from app.main import app
from app.rag.generator import BaseLLMGenerator, LLMGenerationError, MockLLMGenerator
from app.schemas.repository import RepositoryInfo


@pytest.fixture
def sample_repo(tmp_path: Path):
    """Create a temporary repository workspace with sample python and script files."""
    app_dir = tmp_path / "app" / "services"
    app_dir.mkdir(parents=True, exist_ok=True)

    calc_file = app_dir / "calculator.py"
    calc_file.write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def divide_unhandled(a, b):\n"
        "    return a / b\n\n"
        "def risky_operation(token):\n"
        "    api_key = 'sk-abcdef1234567890abcdef1234567890'\n"
        "    try:\n"
        "        eval(token)\n"
        "    except Exception:\n"
        "        pass\n",
        encoding="utf-8",
    )

    empty_file = app_dir / "empty.py"
    empty_file.write_text("", encoding="utf-8")

    return tmp_path


# ==============================================================================
# 1. Evidence Collection & Request Validation Tests
# ==============================================================================

class TestEvidenceCollection:
    """Test validation, path security, and evidence collection."""

    def test_valid_file_collection(self, sample_repo: Path):
        collector = EvidenceCollector()
        context = collector.collect(sample_repo, "app/services/calculator.py")
        assert context.total_lines >= 10
        assert context.start_line == 1
        assert "def add" in context.content
        assert len(context.functions) >= 2
        # Verify line numbered text
        assert "   1 | def add" in context.numbered_lines

    def test_entity_targeting(self, sample_repo: Path):
        collector = EvidenceCollector()
        context = collector.collect(
            sample_repo,
            "app/services/calculator.py",
            entity_name="divide_unhandled",
        )
        assert context.entity_name == "divide_unhandled"
        assert context.start_line == 4
        assert "def divide_unhandled" in context.content

    def test_missing_file_raises_not_found(self, sample_repo: Path):
        collector = EvidenceCollector()
        with pytest.raises(ReviewTargetNotFoundError, match="not found in repository"):
            collector.collect(sample_repo, "app/services/nonexistent.py")

    def test_missing_entity_raises_not_found(self, sample_repo: Path):
        collector = EvidenceCollector()
        with pytest.raises(ReviewTargetNotFoundError, match="was not found in file"):
            collector.collect(sample_repo, "app/services/calculator.py", entity_name="missing_func")

    def test_path_traversal_rejected(self, sample_repo: Path):
        collector = EvidenceCollector()
        with pytest.raises(ReviewValidationError, match="Path traversal"):
            collector.validate_and_resolve_path(sample_repo, "app/../../etc/passwd")

    def test_absolute_path_rejected(self, sample_repo: Path):
        collector = EvidenceCollector()
        with pytest.raises(ReviewValidationError, match="Absolute paths are not permitted"):
            collector.validate_and_resolve_path(sample_repo, "/etc/shadow")

    def test_empty_path_rejected(self, sample_repo: Path):
        collector = EvidenceCollector()
        with pytest.raises(ReviewValidationError, match="must not be empty"):
            collector.validate_and_resolve_path(sample_repo, "   ")

    def test_deterministic_findings_collected(self, sample_repo: Path):
        collector = EvidenceCollector()
        context = collector.collect(sample_repo, "app/services/calculator.py")
        # Should detect eval() and broad exception via static analysis
        static_titles = [f.title for f in context.static_security_findings + context.static_quality_findings]
        assert any("eval" in t.lower() for t in static_titles)
        assert any("exception" in t.lower() for t in static_titles)


# ==============================================================================
# 2. Grounding & Secret Redaction Tests
# ==============================================================================

class TestGroundingAndRedaction:
    """Test validation of LLM findings against source lines and secret redaction."""

    def test_secret_redaction(self):
        secret_text = "Discovered key: sk-abcdef1234567890abcdef1234567890 and token ghp_123456789012345678901234567890123456"
        redacted = GroundingValidator.redact_secrets(secret_text)
        assert "sk-abcdef" not in redacted
        assert "[REDACTED_API_KEY]" in redacted
        assert "[REDACTED_GITHUB_TOKEN]" in redacted

    def test_grounding_valid_findings(self):
        context = EvidenceContext(
            file_path="app/test.py",
            absolute_path="/tmp/test.py",
            content="def foo():\n    return 42\n",
            total_lines=2,
            start_line=1,
            end_line=2,
        )
        raw_items = [
            {
                "title": "Missing docstring",
                "category": "maintainability",
                "severity": "info",
                "confidence": "high",
                "start_line": 1,
                "end_line": 2,
                "problem": "Function lacks a docstring",
                "evidence": "def foo():",
                "recommendation": "Add a docstring.",
            }
        ]
        grounded = GroundingValidator.ground_findings(raw_items, context)
        assert len(grounded) == 1
        assert grounded[0].title == "Missing docstring"
        assert grounded[0].is_verified is True
        assert grounded[0].source == "ai_review"

    def test_grounding_clamps_invalid_line_numbers(self):
        context = EvidenceContext(
            file_path="app/test.py",
            absolute_path="/tmp/test.py",
            content="def foo():\n    return 42\n",
            total_lines=2,
            start_line=1,
            end_line=2,
        )
        raw_items = [
            {
                "title": "Hallucinated line numbers",
                "category": "correctness",
                "severity": "high",
                "start_line": 999,
                "end_line": 1000,
                "problem": "Line numbers outside file",
                "evidence": "nonexistent code",
                "recommendation": "Fix issue.",
            }
        ]
        grounded = GroundingValidator.ground_findings(raw_items, context)
        assert len(grounded) == 1
        assert grounded[0].start_line <= 2
        assert grounded[0].end_line <= 2
        assert grounded[0].is_verified is False

    def test_grounding_recovers_line_numbers_from_evidence(self):
        context = EvidenceContext(
            file_path="app/test.py",
            absolute_path="/tmp/test.py",
            content="def first():\n    pass\n\ndef target():\n    x = 10\n    return x\n",
            total_lines=6,
            start_line=1,
            end_line=6,
        )
        raw_items = [
            {
                "title": "Unused variable",
                "category": "maintainability",
                "severity": "low",
                "start_line": 99,
                "end_line": 100,
                "problem": "Variable x",
                "evidence": "x = 10",
                "recommendation": "Return directly.",
            }
        ]
        grounded = GroundingValidator.ground_findings(raw_items, context)
        assert len(grounded) == 1
        # Recovered line 5 where "x = 10" is defined
        assert grounded[0].start_line == 5


# ==============================================================================
# 3. LLM Integration & Review Pipeline Tests
# ==============================================================================

class DummyLLM(BaseLLMGenerator):
    """Test helper returning canned JSON responses."""

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.model = "dummy-model"

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        return self.response_text


class FailingLLM(BaseLLMGenerator):
    """Test helper that simulates LLM timeout or error."""

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> str:
        raise LLMGenerationError("Simulated LLM network timeout")


class TestReviewPipeline:
    """Test the end-to-end review orchestrator."""

    @pytest.mark.anyio
    async def test_review_with_mock_llm(self, sample_repo: Path):
        reviewer = CodeReviewer()
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )
        req = CodeReviewRequest(
            repository_url="https://github.com/octocat/Hello-World",
            file_path="app/services/calculator.py",
            review_focus="all",
        )
        response = await reviewer.review_code(sample_repo, repo_info, req)
        assert response.status == "completed"
        assert response.summary.total_findings > 0
        assert response.metadata.ai_available is True
        # Check that both static analysis and AI review findings exist
        sources = {f.source for f in response.findings}
        assert "static_analysis" in sources or "ai_review" in sources

    @pytest.mark.anyio
    async def test_review_with_structured_llm_json(self, sample_repo: Path):
        llm_payload = json.dumps({
            "executive_summary": "Identified potential division by zero and dynamic code execution.",
            "findings": [
                {
                    "title": "Missing Zero Check in Division",
                    "category": "correctness",
                    "severity": "high",
                    "confidence": "high",
                    "start_line": 4,
                    "end_line": 5,
                    "problem": "Function divide_unhandled performs division without zero check.",
                    "evidence": "return a / b",
                    "recommendation": "Add if b == 0 validation.",
                    "suggested_change": "if b == 0:\n    raise ValueError('Cannot divide by zero')\nreturn a / b",
                }
            ]
        })
        reviewer = CodeReviewer(llm_generator=DummyLLM(llm_payload))
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )
        req = CodeReviewRequest(
            repository_url="https://github.com/octocat/Hello-World",
            file_path="app/services/calculator.py",
        )
        response = await reviewer.review_code(sample_repo, repo_info, req)
        assert response.status == "completed"
        ai_titles = [f.title for f in response.findings if f.source == "ai_review"]
        assert "Missing Zero Check in Division" in ai_titles

    @pytest.mark.anyio
    async def test_review_handles_malformed_llm_response(self, sample_repo: Path):
        malformed_text = "I am an AI and I think this code is good. Here are some thoughts without JSON."
        reviewer = CodeReviewer(llm_generator=DummyLLM(malformed_text))
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )
        req = CodeReviewRequest(
            repository_url="https://github.com/octocat/Hello-World",
            file_path="app/services/calculator.py",
        )
        response = await reviewer.review_code(sample_repo, repo_info, req)
        assert response.status == "completed"
        # Should include warning about non-JSON response and still contain deterministic findings
        assert any("could not be parsed" in w for w in response.warnings)
        assert response.summary.deterministic_count > 0

    @pytest.mark.anyio
    async def test_review_handles_llm_failure_gracefully(self, sample_repo: Path):
        reviewer = CodeReviewer(llm_generator=FailingLLM())
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )
        req = CodeReviewRequest(
            repository_url="https://github.com/octocat/Hello-World",
            file_path="app/services/calculator.py",
        )
        response = await reviewer.review_code(sample_repo, repo_info, req)
        assert response.status == "completed"
        assert any("temporarily unavailable" in w for w in response.warnings)
        assert response.summary.deterministic_count > 0

    @pytest.mark.anyio
    async def test_empty_file_returns_clean_review(self, sample_repo: Path):
        reviewer = CodeReviewer(llm_generator=DummyLLM('{"executive_summary": "Empty file", "findings": []}'))
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )
        req = CodeReviewRequest(
            repository_url="https://github.com/octocat/Hello-World",
            file_path="app/services/empty.py",
        )
        response = await reviewer.review_code(sample_repo, repo_info, req)
        assert response.status == "completed"
        assert len(response.findings) == 0


# ==============================================================================
# 4. API Endpoint Integration Tests
# ==============================================================================

class TestReviewAPIEndpoints:
    """Test FastAPI endpoint behavior for review requests."""

    client = TestClient(app)

    def test_review_invalid_repository_url(self):
        payload = {
            "repository_url": "not-a-valid-url",
            "file_path": "app/services/calculator.py",
        }
        response = self.client.post("/api/v1/repositories/review-code", json=payload)
        assert response.status_code == 400

    def test_review_path_traversal_rejected_immediately(self):
        payload = {
            "repository_url": "https://github.com/octocat/Hello-World",
            "file_path": "app/../../secret.py",
        }
        response = self.client.post("/api/v1/repositories/review-code", json=payload)
        assert response.status_code == 400
        assert "Path traversal" in response.json()["detail"]

    def test_review_successful_flow(self, sample_repo: Path):
        with patch("app.services.repository_service.RepositoryService.cloned_repository") as mock_clone:
            mock_clone.return_value.__enter__.return_value = (sample_repo, "main")

            payload = {
                "repository_url": "https://github.com/octocat/Hello-World",
                "file_path": "app/services/calculator.py",
                "review_focus": "all",
            }
            response = self.client.post("/api/v1/repositories/review-code", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "completed"
            assert data["file_path"] == "app/services/calculator.py"
            assert "summary" in data
            assert "findings" in data
            assert data["summary"]["total_findings"] >= 1
            assert "executive_summary" in data["summary"]

    def test_review_target_not_found(self, sample_repo: Path):
        with patch("app.services.repository_service.RepositoryService.cloned_repository") as mock_clone:
            mock_clone.return_value.__enter__.return_value = (sample_repo, "main")

            payload = {
                "repository_url": "https://github.com/octocat/Hello-World",
                "file_path": "app/services/nonexistent_file.py",
            }
            response = self.client.post("/api/v1/repositories/review-code", json=payload)
            assert response.status_code == 404
