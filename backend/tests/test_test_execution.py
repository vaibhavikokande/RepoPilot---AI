"""Comprehensive unit and integration tests for Day 10 test execution and coverage analysis."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.repository import RepositoryInfo
from app.schemas.test_execution import (
    CoverageReport,
    FileCoverage,
    SandboxInfo,
    SandboxStatus,
    TestCaseResult,
    TestRunRequest,
    TestRunResponse,
    TestSummary,
)
from app.test_execution.coverage import CoverageParser
from app.test_execution.models import (
    RequestValidationError,
    SandboxExecutionResult,
    SandboxUnavailableError,
)
from app.test_execution.reporting import TestReporter
from app.test_execution.runner import TestRunner, test_run_store
from app.test_execution.sandbox import (
    DockerSandbox,
    MockSandbox,
    create_sandbox,
    get_sandbox_status,
)


@pytest.fixture
def sample_repo(tmp_path: Path):
    """Create a temporary repository workspace with sample source and test files."""
    app_dir = tmp_path / "app" / "services"
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    calc_file = app_dir / "calculator.py"
    calc_file.write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def divide(a: float, b: float) -> float:\n"
        "    if b == 0:\n"
        "        raise ZeroDivisionError('division by zero')\n"
        "    return a / b\n",
        encoding="utf-8",
    )

    test_file = tests_dir / "test_calculator.py"
    test_file.write_text(
        "import pytest\n"
        "from app.services.calculator import add, divide\n\n"
        "def test_add_success():\n"
        "    assert add(2, 3) == 5\n\n"
        "def test_divide_success():\n"
        "    assert divide(10.0, 2.0) == 5.0\n",
        encoding="utf-8",
    )

    return tmp_path


# ==============================================================================
# 1. Request Validation Tests
# ==============================================================================

class TestRequestValidation:
    """Test security constraints and input validation on test execution requests."""

    def test_valid_request(self, sample_repo: Path):
        runner = TestRunner()
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_calculator.py",
            target_file="app/services/calculator.py",
            timeout_seconds=30,
        )
        test_path, target_path = runner.validate_request(req, sample_repo)
        assert test_path.is_file()
        assert target_path is not None and target_path.is_file()

    def test_missing_test_file_rejected(self, sample_repo: Path):
        runner = TestRunner()
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_nonexistent.py",
        )
        with pytest.raises(FileNotFoundError, match="not found in repository"):
            runner.validate_request(req, sample_repo)

    def test_absolute_path_rejected(self, sample_repo: Path):
        runner = TestRunner()
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="/etc/passwd",
        )
        with pytest.raises(RequestValidationError, match="Absolute paths are not allowed"):
            runner.validate_request(req, sample_repo)

    def test_path_traversal_rejected(self, sample_repo: Path):
        runner = TestRunner()
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/../../secret.py",
        )
        with pytest.raises(RequestValidationError, match="Path traversal sequences"):
            runner.validate_request(req, sample_repo)

    def test_unsupported_file_extension_rejected(self, sample_repo: Path):
        runner = TestRunner()
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_runner.sh",
        )
        with pytest.raises(RequestValidationError, match="Only Python \\(\\.py\\) files are supported"):
            runner.validate_request(req, sample_repo)

    def test_invalid_timeout_rejected(self, sample_repo: Path):
        # Timeout < 1 rejected by Pydantic or runner
        with pytest.raises(Exception):
            TestRunRequest(
                repository_url="https://github.com/octocat/Hello-World",
                test_file="tests/test_calculator.py",
                timeout_seconds=0,
            )

        with pytest.raises(Exception):
            TestRunRequest(
                repository_url="https://github.com/octocat/Hello-World",
                test_file="tests/test_calculator.py",
                timeout_seconds=100,
            )

    def test_valid_inline_test_code_accepted(self, sample_repo: Path):
        runner = TestRunner()
        valid_code = "def test_generated():\n    assert 1 + 1 == 2\n"
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_generated.py",
            test_code=valid_code,
        )
        test_path, _ = runner.validate_request(req, sample_repo)
        assert test_path.name == "test_generated.py"

    def test_invalid_inline_test_code_syntax_rejected(self, sample_repo: Path):
        runner = TestRunner()
        invalid_code = "def test_broken(:\n    assert True"
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_broken.py",
            test_code=invalid_code,
        )
        with pytest.raises(RequestValidationError, match="invalid Python syntax"):
            runner.validate_request(req, sample_repo)


# ==============================================================================
# 2. Reporting and Output Parsing Tests
# ==============================================================================

class TestReporting:
    """Test parsing of pytest outcomes, summary lines, and error detection."""

    def test_all_tests_passed(self):
        stdout = (
            "tests/test_math.py::test_add PASSED [ 50%]\n"
            "tests/test_math.py::test_sub PASSED [100%]\n"
            "============================== 2 passed in 0.12s ==============================="
        )
        summary, results, warnings = TestReporter.parse_output(stdout, "", exit_code=0)
        assert summary.total == 2
        assert summary.passed == 2
        assert summary.failed == 0
        assert summary.skipped == 0
        assert summary.errors == 0
        assert len(results) == 2
        assert results[0].name == "test_add"
        assert results[0].status == "passed"

    def test_mixed_results_with_failure_and_skip(self):
        stdout = (
            "tests/test_math.py::test_add PASSED [ 33%]\n"
            "tests/test_math.py::test_div FAILED [ 66%]\n"
            "tests/test_math.py::test_exp SKIPPED [100%]\n"
            "=================== 1 failed, 1 passed, 1 skipped in 0.45s ===================="
        )
        summary, results, warnings = TestReporter.parse_output(stdout, "", exit_code=1)
        assert summary.total == 3
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.skipped == 1
        assert summary.errors == 0

    def test_collection_error_and_missing_dependency(self):
        stdout = (
            "ERROR collecting tests/test_api.py\n"
            "ModuleNotFoundError: No module named 'requests'\n"
            "=========================== 1 error in 0.05s ==========================="
        )
        summary, results, warnings = TestReporter.parse_output(stdout, "", exit_code=2)
        assert summary.errors >= 1
        assert any("Missing dependency 'requests'" in w for w in warnings)

    def test_sanitization_removes_server_paths_and_tokens(self):
        raw = (
            "Traceback in /workspace/app/service.py:10\n"
            "Loaded from /tmp/repopilot_test_run_12345/tests/test_run.py\n"
            "API token: sk-1234567890abcdef1234567890\n"
        )
        sanitized = TestReporter.sanitize_text(raw)
        assert "/workspace/" not in sanitized
        assert "/tmp/repopilot_" not in sanitized
        assert "[REDACTED_API_KEY]" in sanitized


# ==============================================================================
# 3. Coverage Parser Tests
# ==============================================================================

class TestCoverageParser:
    """Test parsing and metrics calculation for coverage reports."""

    def test_parse_valid_coverage_data(self):
        cov_data = {
            "files": {
                "/workspace/app/services/calculator.py": {
                    "summary": {
                        "num_statements": 10,
                        "covered_lines": 8,
                        "missing_lines": 2,
                        "percent_covered": 80.0,
                    },
                    "missing_lines": [5, 6],
                }
            },
            "totals": {
                "num_statements": 10,
                "covered_lines": 8,
                "missing_lines": 2,
                "percent_covered": 80.0,
            },
        }
        report = CoverageParser.parse_dict(cov_data, target_file="app/services/calculator.py")
        assert report.is_available is True
        assert report.total_statements == 10
        assert report.covered_statements == 8
        assert report.missing_statements == 2
        assert report.coverage_percent == 80.0
        assert len(report.files) == 1
        assert report.files[0].file_path == "app/services/calculator.py"
        assert report.files[0].missing_lines == [5, 6]

    def test_coverage_missing_file_reports_unavailable(self, tmp_path: Path):
        nonexistent = tmp_path / "nonexistent.json"
        report = CoverageParser.parse_file(nonexistent)
        assert report.is_available is False
        assert "not generated" in (report.reason or "")

    def test_empty_coverage_file_reports_unavailable(self, tmp_path: Path):
        empty_file = tmp_path / "coverage.json"
        empty_file.write_text("", encoding="utf-8")
        report = CoverageParser.parse_file(empty_file)
        assert report.is_available is False
        assert "empty" in (report.reason or "")

    def test_malformed_coverage_file_reports_unavailable(self, tmp_path: Path):
        broken = tmp_path / "broken.json"
        broken.write_text("{invalid json", encoding="utf-8")
        report = CoverageParser.parse_file(broken)
        assert report.is_available is False
        assert "Failed to parse" in (report.reason or "")

    def test_empty_statements_handles_division_by_zero(self):
        cov_data = {
            "files": {
                "app/__init__.py": {
                    "summary": {
                        "num_statements": 0,
                        "covered_lines": 0,
                        "missing_lines": 0,
                        "percent_covered": 100.0,
                    },
                    "missing_lines": [],
                }
            },
            "totals": {
                "num_statements": 0,
                "covered_lines": 0,
                "missing_lines": 0,
                "percent_covered": 0.0,
            },
        }
        report = CoverageParser.parse_dict(cov_data)
        assert report.is_available is True
        assert report.coverage_percent == 0.0


# ==============================================================================
# 4. Sandbox Safety and Execution Tests
# ==============================================================================

class TestSandboxSafety:
    """Test sandbox configuration, resource isolation, and safety invariants."""

    def test_docker_sandbox_info_reflects_security_constraints(self):
        sandbox = DockerSandbox()
        info = sandbox.get_info()
        assert info.sandbox_type == "docker"
        assert info.is_isolated is True
        assert info.network_disabled is True
        assert info.non_root is True
        assert info.resource_limits["memory"] == "512m"
        assert info.resource_limits["cpus"] == "1.0"
        assert info.resource_limits["pids"] == 64

    def test_docker_unavailable_raises_sandbox_unavailable_error(self):
        with patch("shutil.which", return_value=None):
            with pytest.raises(SandboxUnavailableError, match="Docker container runtime is not detected"):
                create_sandbox(allow_mock=False)

    def test_allow_mock_returns_mock_sandbox_when_docker_missing(self):
        with patch("shutil.which", return_value=None):
            sandbox = create_sandbox(allow_mock=True)
            assert isinstance(sandbox, MockSandbox)

    def test_sandbox_status_diagnostic(self):
        with patch("shutil.which", return_value=None):
            status = get_sandbox_status()
            assert status.available is False
            assert "Container sandbox runtime" in status.message
            assert len(status.requirements) >= 5

        with patch("shutil.which", return_value="/usr/local/bin/docker"):
            status = get_sandbox_status()
            assert status.available is True
            assert status.configured is True

    @pytest.mark.anyio
    async def test_original_repo_remains_unchanged_after_run(self, sample_repo: Path):
        """Verify that running tests operates on disposable copy and original files remain intact."""
        test_file = sample_repo / "tests" / "test_calculator.py"
        original_content = test_file.read_text(encoding="utf-8")
        original_files = set(p.relative_to(sample_repo) for p in sample_repo.rglob("*"))

        runner = TestRunner(sandbox=MockSandbox())
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_calculator.py",
            coverage=True,
            allow_mock=True,
        )
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )

        response = await runner.run_tests(req, sample_repo, repo_info)
        assert response.status == "completed"

        # Verify original files are 100% identical
        assert test_file.read_text(encoding="utf-8") == original_content
        current_files = set(p.relative_to(sample_repo) for p in sample_repo.rglob("*"))
        assert original_files == current_files

    @pytest.mark.anyio
    async def test_mock_sandbox_simulates_timeout(self, sample_repo: Path):
        timeout_sandbox = MockSandbox(simulate_timeout=True)
        runner = TestRunner(sandbox=timeout_sandbox)
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_calculator.py",
            timeout_seconds=5,
            allow_mock=True,
        )
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )

        response = await runner.run_tests(req, sample_repo, repo_info)
        assert response.status == "timed_out"
        assert response.exit_code == -1

    @pytest.mark.anyio
    async def test_run_id_saved_in_store(self, sample_repo: Path):
        runner = TestRunner(sandbox=MockSandbox())
        req = TestRunRequest(
            repository_url="https://github.com/octocat/Hello-World",
            test_file="tests/test_calculator.py",
            allow_mock=True,
        )
        repo_info = RepositoryInfo(
            name="Hello-World",
            owner="octocat",
            url="https://github.com/octocat/Hello-World",
        )

        response = await runner.run_tests(req, sample_repo, repo_info)
        stored = test_run_store.get_run(response.run_id)
        assert stored is not None
        assert stored.run_id == response.run_id


# ==============================================================================
# 5. API Endpoint Tests
# ==============================================================================

class TestExecutionAPIEndpoints:
    """Test API integration for running tests and fetching run status."""

    client = TestClient(app)

    def test_sandbox_status_endpoint(self):
        response = self.client.get("/api/v1/repositories/sandbox-status")
        assert response.status_code == 200
        data = response.json()
        assert "available" in data
        assert "sandbox_type" in data
        assert "requirements" in data

    def test_run_tests_invalid_repo_url(self):
        payload = {
            "repository_url": "invalid-url",
            "test_file": "tests/test_calc.py",
        }
        response = self.client.post("/api/v1/repositories/run-tests", json=payload)
        assert response.status_code == 400

    def test_run_tests_path_traversal_rejected(self):
        payload = {
            "repository_url": "https://github.com/octocat/Hello-World",
            "test_file": "tests/../../etc/passwd",
        }
        response = self.client.post("/api/v1/repositories/run-tests", json=payload)
        assert response.status_code == 400

    def test_run_tests_successful_mock_flow(self, sample_repo: Path):
        with patch("app.services.repository_service.RepositoryService.cloned_repository") as mock_clone:
            mock_clone.return_value.__enter__.return_value = (sample_repo, "main")

            payload = {
                "repository_url": "https://github.com/octocat/Hello-World",
                "test_file": "tests/test_calculator.py",
                "coverage": True,
                "allow_mock": True,
            }

            response = self.client.post("/api/v1/repositories/run-tests", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "completed"
            assert data["summary"]["total"] >= 1
            assert data["run_id"] is not None
            assert data["coverage"] is not None
            assert data["execution_type"] == "mocked"

            # Check that GET /api/v1/test-runs/{run_id} returns the same data
            get_resp = self.client.get(f"/api/v1/test-runs/{data['run_id']}")
            assert get_resp.status_code == 200
            assert get_resp.json()["run_id"] == data["run_id"]

            # Also check repository-nested endpoint alias
            alias_resp = self.client.get(f"/api/v1/repositories/test-runs/{data['run_id']}")
            assert alias_resp.status_code == 200
            assert alias_resp.json()["run_id"] == data["run_id"]

    def test_get_nonexistent_test_run_returns_404(self):
        response = self.client.get("/api/v1/test-runs/nonexistent-run-id-12345")
        assert response.status_code == 404
