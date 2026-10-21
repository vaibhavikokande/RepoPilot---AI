"""Domain models and exceptions for test execution."""

from dataclasses import dataclass
from typing import Optional

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


class TestExecutionError(Exception):
    """Base exception for all test execution operations."""


class RequestValidationError(TestExecutionError):
    """Raised when the test execution request fails validation."""


class SandboxUnavailableError(TestExecutionError):
    """Raised when secure container sandbox environment is unavailable."""


class DependencyUnavailableError(TestExecutionError):
    """Raised when repository dependencies are unavailable in runner."""


class ExecutionTimeoutError(TestExecutionError):
    """Raised when test execution exceeds configured timeout."""


@dataclass
class SandboxExecutionResult:
    """Raw result returned by sandbox environment run."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    error: Optional[str] = None


__all__ = [
    "CoverageReport",
    "DependencyUnavailableError",
    "ExecutionTimeoutError",
    "FileCoverage",
    "RequestValidationError",
    "SandboxExecutionResult",
    "SandboxInfo",
    "SandboxStatus",
    "SandboxUnavailableError",
    "TestCaseResult",
    "TestExecutionError",
    "TestRunRequest",
    "TestRunResponse",
    "TestSummary",
]
