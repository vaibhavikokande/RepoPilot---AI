"""Comprehensive unit and integration tests for Day 12 AI Debugging Assistant."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.debug_assistant.assistant import DebugAssistant
from app.debug_assistant.context_locator import ContextLocator
from app.debug_assistant.error_parser import parse_error
from app.debug_assistant.models import (
    DebugRequest,
    DebugResponse,
    DebugValidationError,
    ParsedError,
    PossibleCause,
    RetrievedContext,
    SourceEvidence,
    StackFrame,
)
from app.debug_assistant.prompt_builder import DebugPromptBuilder
from app.debug_assistant.validator import DebugValidator
from app.main import app
from app.rag.generator import BaseLLMGenerator, LLMGenerationError, MockLLMGenerator
from app.schemas.repository import RepositoryInfo


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a temporary repository workspace with sample code files."""
    app_dir = tmp_path / "app" / "services"
    app_dir.mkdir(parents=True, exist_ok=True)

    calc_file = app_dir / "calculator.py"
    calc_file.write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def divide(a: float, b: float) -> float:\n"
        "    # Potential zero division\n"
        "    return a / b\n\n"
        "def process_user_data(data: dict) -> str:\n"
        "    # Potential KeyError\n"
        "    return data['user_id']\n",
        encoding="utf-8",
    )

    auth_file = app_dir / "auth.js"
    auth_file.write_text(
        "function verifyToken(token) {\n"
        "    if (!token) throw new TypeError('Token cannot be null');\n"
        "    return token.split('.')[1];\n"
        "}\n",
        encoding="utf-8",
    )

    return tmp_path


# ==============================================================================
# 1. Error Parser Tests
# ==============================================================================

class TestErrorParser:
    """Test parsing of Python, JavaScript, and unrecognized error formats."""

    def test_parse_python_traceback(self):
        trace = (
            "Traceback (most recent call last):\n"
            '  File "app/services/calculator.py", line 5, in divide\n'
            "    return a / b\n"
            "ZeroDivisionError: float division by zero\n"
        )
        parsed = parse_error(trace)
        assert parsed.language == "python"
        assert parsed.error_type == "ZeroDivisionError"
        assert "division by zero" in parsed.error_message
        assert len(parsed.frames) == 1
        assert parsed.frames[0].file_path == "app/services/calculator.py"
        assert parsed.frames[0].line_number == 5
        assert parsed.frames[0].function_name == "divide"
        assert "app/services/calculator.py" in parsed.file_paths

    def test_parse_multi_frame_python_traceback(self):
        trace = (
            "Traceback (most recent call last):\n"
            '  File "main.py", line 12, in <module>\n'
            "    result = calculate()\n"
            '  File "app/services/calculator.py", line 9, in process_user_data\n'
            "    return data['user_id']\n"
            "KeyError: 'user_id'\n"
        )
        parsed = parse_error(trace)
        assert parsed.error_type == "KeyError"
        assert "'user_id'" in parsed.error_message
        assert len(parsed.frames) == 2
        assert parsed.frames[1].line_number == 9
        assert parsed.frames[1].function_name == "process_user_data"

    def test_parse_javascript_traceback(self):
        trace = (
            "TypeError: Cannot read properties of undefined (reading 'length')\n"
            "    at verifyToken (app/services/auth.js:3:18)\n"
            "    at processRequest (/var/app/server.js:45:10)\n"
        )
        parsed = parse_error(trace)
        assert parsed.language == "javascript"
        assert parsed.error_type == "TypeError"
        assert "Cannot read properties" in parsed.error_message
        assert len(parsed.frames) == 2
        assert parsed.frames[0].file_path == "app/services/auth.js"
        assert parsed.frames[0].line_number == 3
        assert parsed.frames[0].function_name == "verifyToken"

    def test_parse_unrecognized_error_format(self):
        raw_text = "FATAL: Connection to database failed after 3 retries (timeout: 30s) at db/pool.py:102"
        parsed = parse_error(raw_text)
        assert "Connection to database failed" in parsed.error_message
        assert len(parsed.file_paths) >= 1
        assert "db/pool.py" in parsed.file_paths[0]

    def test_empty_input_handled_gracefully(self):
        parsed = parse_error("")
        assert parsed.error_message == ""
        assert len(parsed.frames) == 0


# ==============================================================================
# 2. Context Locator & Path Safety Tests
# ==============================================================================

class TestContextLocator:
    """Test source file location, path validation, and security boundaries."""

    def test_resolve_exact_relative_path(self, sample_repo: Path):
        locator = ContextLocator()
        resolved = locator.resolve_repo_relative_path(sample_repo, "app/services/calculator.py")
        assert resolved == "app/services/calculator.py"

    def test_resolve_nested_absolute_path_suffix(self, sample_repo: Path):
        locator = ContextLocator()
        # Stack traces often have container prefixes like /var/workspace/app/services/calculator.py
        resolved = locator.resolve_repo_relative_path(
            sample_repo, "/usr/src/my_app/app/services/calculator.py"
        )
        assert resolved == "app/services/calculator.py"

    def test_path_traversal_rejected(self, sample_repo: Path):
        locator = ContextLocator()
        resolved = locator.resolve_repo_relative_path(sample_repo, "../../etc/passwd")
        assert resolved is None

    def test_validate_file_path_traversal_raises_error(self, sample_repo: Path):
        locator = ContextLocator()
        with pytest.raises(DebugValidationError, match="escapes repository boundary"):
            locator.validate_file_path(sample_repo, "app/../../secret.txt")

    def test_locate_context_success(self, sample_repo: Path):
        locator = ContextLocator()
        trace = (
            "Traceback (most recent call last):\n"
            '  File "app/services/calculator.py", line 5, in divide\n'
            "    return a / b\n"
            "ZeroDivisionError: float division by zero\n"
        )
        parsed = parse_error(trace)
        context = locator.locate_context(sample_repo, parsed)

        assert context.has_exact_source is True
        assert len(context.evidence_items) == 1
        ev = context.evidence_items[0]
        assert ev.file_path == "app/services/calculator.py"
        assert ev.start_line <= 5 <= ev.end_line
        assert "return a / b" in ev.code_snippet
        assert ev.entity_name == "divide"

    def test_missing_source_file_tracked(self, sample_repo: Path):
        locator = ContextLocator()
        trace = (
            "Traceback (most recent call last):\n"
            '  File "app/missing_module.py", line 22, in do_work\n'
            "    pass\n"
            "RuntimeError: failed\n"
        )
        parsed = parse_error(trace)
        context = locator.locate_context(sample_repo, parsed)

        assert context.has_exact_source is False
        assert len(context.missing_files) == 1
        assert "app/missing_module.py" in context.missing_files[0]


# ==============================================================================
# 3. Grounding Validator & Secret Redaction Tests
# ==============================================================================

class TestDebugValidator:
    """Test secret redaction, confidence calibration, and file filtering."""

    def test_secret_redaction(self):
        validator = DebugValidator()
        dirty_text = "API key sk-1234567890abcdef1234567890 and token ghp_abcdefghijklmnopqrstuvwx"
        clean = validator.redact_secrets(dirty_text)
        assert "sk-1234567890abcdef1234567890" not in clean
        assert "[REDACTED_API_KEY]" in clean
        assert "ghp_abcdefghijklmnopqrstuvwx" not in clean
        assert "[REDACTED_GITHUB_TOKEN]" in clean

    def test_confidence_downgraded_when_no_source(self):
        validator = DebugValidator()
        empty_context = RetrievedContext(has_exact_source=False)
        calibrated = validator.validate_confidence("high", empty_context)
        assert calibrated == "medium"

    def test_confidence_preserved_when_source_available(self):
        validator = DebugValidator()
        context_with_source = RetrievedContext(has_exact_source=True)
        calibrated = validator.validate_confidence("high", context_with_source)
        assert calibrated == "high"

    def test_filter_related_files(self):
        validator = DebugValidator()
        context = RetrievedContext(related_files=["app/services/calc.py"])
        filtered = validator.filter_related_files(
            ["app/services/calc.py", "invalid/nonexistent.py", "../escape.py"],
            context,
        )
        assert "app/services/calc.py" in filtered
        assert "invalid/nonexistent.py" not in filtered
        assert "../escape.py" not in filtered


# ==============================================================================
# 4. Debug Assistant Pipeline & Fallback Tests
# ==============================================================================

class TestDebugAssistantPipeline:
    """Test full assistant execution with mock and custom LLM generators."""

    @pytest.mark.anyio
    async def test_deterministic_diagnosis_flow(self, sample_repo: Path):
        assistant = DebugAssistant(llm_generator=MockLLMGenerator())
        repo_info = RepositoryInfo(
            name="test-repo",
            owner="octocat",
            url="https://github.com/octocat/test-repo",
        )
        request = DebugRequest(
            repository_url="https://github.com/octocat/test-repo",
            error_message=(
                "Traceback (most recent call last):\n"
                '  File "app/services/calculator.py", line 5, in divide\n'
                "    return a / b\n"
                "ZeroDivisionError: float division by zero\n"
            ),
            reproduction_steps="Call divide(10.0, 0.0)",
            expected_behavior="Return 0.0 or raise ValueError",
        )

        response = await assistant.diagnose_error(sample_repo, repo_info, request)

        assert response.status == "completed"
        assert response.error_type == "ZeroDivisionError"
        assert "division by zero" in response.error_summary
        assert len(response.evidence) == 1
        assert response.evidence[0].file_path == "app/services/calculator.py"
        assert len(response.possible_causes) >= 1
        assert len(response.recommended_steps) >= 1
        assert response.confidence in ("high", "medium", "low")
        assert response.confidence_note != ""
        assert response.suggested_fix is not None

    @pytest.mark.anyio
    async def test_llm_json_parsing_and_synthesis(self, sample_repo: Path):
        mock_llm = AsyncMock(spec=BaseLLMGenerator)
        mock_llm.generate.return_value = json.dumps({
            "error_type": "ZeroDivisionError",
            "error_summary": "Attempted division by zero inside the divide function.",
            "root_cause": "The divide function in app/services/calculator.py divides by b without guarding against 0.",
            "confidence": "high",
            "possible_causes": [
                {
                    "rank": 1,
                    "title": "Zero denominator input",
                    "explanation": "b was passed as 0.0 without validation.",
                    "confidence": "high",
                    "supporting_evidence": ["app/services/calculator.py:5"],
                }
            ],
            "recommended_steps": [
                "1. Add defensive check if b == 0.",
                "2. Raise ValueError with user-friendly message.",
            ],
            "suggested_fix": "if b == 0:\n    raise ValueError('Denominator cannot be zero')\nreturn a / b",
            "missing_information": [],
            "limitations": ["Static analysis only"],
            "related_files": ["app/services/calculator.py"],
        })

        assistant = DebugAssistant(llm_generator=mock_llm)
        repo_info = RepositoryInfo(
            name="test-repo",
            owner="octocat",
            url="https://github.com/octocat/test-repo",
        )
        request = DebugRequest(
            repository_url="https://github.com/octocat/test-repo",
            error_message="ZeroDivisionError: float division by zero at app/services/calculator.py:5",
        )

        response = await assistant.diagnose_error(sample_repo, repo_info, request)

        assert response.error_type == "ZeroDivisionError"
        assert "app/services/calculator.py" in response.root_cause
        assert response.confidence == "high"
        assert len(response.possible_causes) == 1
        assert response.possible_causes[0].rank == 1
        assert "raise ValueError" in response.suggested_fix

    @pytest.mark.anyio
    async def test_llm_failure_gracefully_falls_back(self, sample_repo: Path):
        mock_llm = AsyncMock(spec=BaseLLMGenerator)
        mock_llm.generate.side_effect = LLMGenerationError("API connection timed out after 45s")

        assistant = DebugAssistant(llm_generator=mock_llm)
        repo_info = RepositoryInfo(
            name="test-repo",
            owner="octocat",
            url="https://github.com/octocat/test-repo",
        )
        request = DebugRequest(
            repository_url="https://github.com/octocat/test-repo",
            error_message="KeyError: 'user_id' at app/services/calculator.py:9",
        )

        response = await assistant.diagnose_error(sample_repo, repo_info, request)

        assert response.status == "completed"
        assert response.error_type == "KeyError"
        assert any("fallback" in w.lower() for w in response.warnings)
        assert len(response.possible_causes) >= 1

    @pytest.mark.anyio
    async def test_excessive_input_raises_validation_error(self, sample_repo: Path):
        from pydantic import ValidationError
        huge_error = "A" * 20_000
        with pytest.raises(ValidationError):
            DebugRequest(
                repository_url="https://github.com/octocat/test-repo",
                error_message=huge_error,
            )


# ==============================================================================
# 5. API Endpoint Tests
# ==============================================================================

class TestDebugAPIEndpoint:
    """Test POST /api/v1/repositories/debug endpoint."""

    @pytest.fixture(autouse=True)
    def setup_client(self):
        self.client = TestClient(app)

    def test_invalid_repository_url_rejected(self):
        payload = {
            "repository_url": "invalid-url",
            "error_message": "ZeroDivisionError: division by zero",
        }
        res = self.client.post("/api/v1/repositories/debug", json=payload)
        assert res.status_code == 400
        assert "HTTPS" in res.json()["detail"] or "Invalid" in res.json()["detail"]

    def test_empty_error_message_rejected(self):
        payload = {
            "repository_url": "https://github.com/octocat/Hello-World",
            "error_message": "   ",
        }
        res = self.client.post("/api/v1/repositories/debug", json=payload)
        assert res.status_code == 400
        assert "error_message cannot be empty" in res.json()["detail"]

    def test_path_traversal_in_file_path_rejected(self):
        payload = {
            "repository_url": "https://github.com/octocat/Hello-World",
            "error_message": "RuntimeError: bug",
            "file_path": "../etc/passwd",
        }
        res = self.client.post("/api/v1/repositories/debug", json=payload)
        assert res.status_code == 400
        assert "Path traversal" in res.json()["detail"]

    def test_successful_debug_api_flow(self, sample_repo: Path):
        with patch("app.services.repository_service.RepositoryService.cloned_repository") as mock_clone:
            mock_clone.return_value.__enter__.return_value = (sample_repo, "main")

            payload = {
                "repository_url": "https://github.com/octocat/Hello-World",
                "error_message": (
                    "Traceback (most recent call last):\n"
                    '  File "app/services/calculator.py", line 5, in divide\n'
                    "    return a / b\n"
                    "ZeroDivisionError: float division by zero\n"
                ),
                "reproduction_steps": "Run divide(10, 0)",
            }
            res = self.client.post("/api/v1/repositories/debug", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert data["error_type"] == "ZeroDivisionError"
            assert data["status"] == "completed"
            assert len(data["evidence"]) >= 1
            assert data["evidence"][0]["file_path"] == "app/services/calculator.py"
            assert len(data["possible_causes"]) >= 1
            assert len(data["recommended_steps"]) >= 1
            assert data["confidence"] in ("high", "medium", "low")
