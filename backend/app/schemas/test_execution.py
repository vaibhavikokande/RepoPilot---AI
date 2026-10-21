"""Domain models and Pydantic schemas for safe test execution and coverage analysis."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class TestCaseResult(BaseModel):
    """Result of an individual executed test function."""

    __test__ = False

    name: str = Field(..., description="Name of the test function or method")
    status: str = Field(..., description="Execution outcome: 'passed', 'failed', 'skipped', or 'error'")
    duration_seconds: float = Field(0.0, description="Execution duration in seconds")
    message: Optional[str] = Field(None, description="Failure traceback or skip reason")


class TestSummary(BaseModel):
    """Aggregated outcome counts for the test run."""

    __test__ = False

    total: int = Field(0, description="Total number of test functions collected")
    passed: int = Field(0, description="Number of passed tests")
    failed: int = Field(0, description="Number of failed tests")
    skipped: int = Field(0, description="Number of skipped tests")
    errors: int = Field(0, description="Number of collection or environment errors")


class FileCoverage(BaseModel):
    """Line-level code coverage details for an individual source file."""

    __test__ = False

    file_path: str = Field(..., description="Repository-relative path of the analyzed source file")
    total_statements: int = Field(0, description="Total executable statements in the file")
    covered_statements: int = Field(0, description="Executed statements during test run")
    missing_statements: int = Field(0, description="Unexecuted statements during test run")
    coverage_percent: float = Field(0.0, description="Coverage percentage (0.0 - 100.0)")
    missing_lines: List[int] = Field(default_factory=list, description="1-indexed line numbers of uncovered statements")


class CoverageReport(BaseModel):
    """Overall coverage analysis summary."""

    __test__ = False

    total_statements: int = Field(0, description="Total statements across all analyzed files")
    covered_statements: int = Field(0, description="Total covered statements")
    missing_statements: int = Field(0, description="Total missing statements")
    coverage_percent: float = Field(0.0, description="Aggregate coverage percentage (0.0 - 100.0)")
    files: List[FileCoverage] = Field(default_factory=list, description="Per-file coverage breakdown")
    is_available: bool = Field(True, description="Whether coverage data was successfully collected")
    reason: Optional[str] = Field(None, description="Explanation if coverage was unavailable or skipped")


class SandboxInfo(BaseModel):
    """Metadata describing the isolation environment used for execution."""

    sandbox_type: str = Field("docker", description="Sandbox runtime type: 'docker', 'mock', or 'none'")
    is_isolated: bool = Field(True, description="Whether the runner is executed in an isolated sandbox")
    network_disabled: bool = Field(True, description="Whether network access was disabled")
    non_root: bool = Field(True, description="Whether execution runs as an unprivileged user")
    resource_limits: Dict[str, Any] = Field(
        default_factory=lambda: {"memory": "512m", "cpus": "1.0", "pids": 64},
        description="Enforced hardware and operating system resource limits",
    )
    runner_image: Optional[str] = Field(None, description="Container image tag used for execution")


class SandboxStatus(BaseModel):
    """Server diagnostic status for isolated container sandbox execution."""

    available: bool = Field(..., description="Whether containerized execution sandbox is available on host")
    sandbox_type: str = Field("docker", description="Detected sandbox implementation type")
    configured: bool = Field(..., description="Whether required container runner image is ready")
    message: str = Field(..., description="Diagnostic explanation or setup instructions")
    requirements: List[str] = Field(
        default_factory=list,
        description="Security constraints enforced by the sandbox",
    )


class TestRunRequest(BaseModel):
    """Request payload to trigger an approved test execution."""

    __test__ = False

    repository_url: str = Field(..., description="Public GitHub repository URL (https://github.com/owner/repo)")
    test_file: str = Field(..., description="Repository-relative path of the test file to run (e.g. 'tests/test_calc.py')")
    test_code: Optional[str] = Field(
        None,
        description="Optional inline test source code to run (e.g. newly generated tests from Day 9)",
    )
    target_file: Optional[str] = Field(
        None,
        description="Optional source file for focused line-level coverage analysis (e.g. 'app/services/calc.py')",
    )
    coverage: bool = Field(True, description="Whether to collect statement coverage using coverage.py")
    timeout_seconds: int = Field(30, ge=1, le=60, description="Maximum execution timeout in seconds (1-60)")
    allow_mock: bool = Field(
        False,
        description="Allow mock execution for testing or demonstration when container sandbox is offline",
    )


class TestRunResponse(BaseModel):
    """Complete test run report including results, coverage, and logs."""

    __test__ = False

    run_id: str = Field(..., description="Unique execution run identifier (UUID)")
    status: str = Field(
        ...,
        description="Execution status: 'completed', 'failed', 'timed_out', 'failed_to_start', 'rejected', 'running'",
    )
    test_file: str = Field(..., description="Path of the executed test file")
    target_file: Optional[str] = Field(None, description="Target source file for coverage if specified")
    summary: TestSummary = Field(default_factory=TestSummary, description="Aggregated test outcome counts")
    test_results: List[TestCaseResult] = Field(default_factory=list, description="Per-test execution details")
    duration_seconds: float = Field(0.0, description="Total execution duration in seconds")
    exit_code: Optional[int] = Field(None, description="Pytest process exit code")
    coverage: Optional[CoverageReport] = Field(None, description="Coverage analysis report if collected")
    sandbox: SandboxInfo = Field(..., description="Sandbox security configuration metadata")
    execution_type: str = Field("container", description="Execution type: 'container', 'mocked', or 'none'")
    stdout: str = Field("", description="Captured standard output (truncated safely)")
    stderr: str = Field("", description="Captured standard error (truncated safely)")
    error_message: Optional[str] = Field(None, description="Runner error message if execution failed")
    warnings: List[str] = Field(default_factory=list, description="Operational or security warnings")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Timestamp when the run was initiated",
    )
