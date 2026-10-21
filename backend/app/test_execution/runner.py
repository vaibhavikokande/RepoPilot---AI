"""Test runner orchestrating isolated execution and coverage calculation."""

import ast
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from app.schemas.repository import RepositoryInfo
from app.schemas.test_execution import (
    CoverageReport,
    SandboxInfo,
    TestRunRequest,
    TestRunResponse,
    TestSummary,
)
from app.test_execution.coverage import CoverageParser
from app.test_execution.models import (
    ExecutionTimeoutError,
    RequestValidationError,
    SandboxUnavailableError,
)
from app.test_execution.reporting import TestReporter
from app.test_execution.sandbox import (
    BaseSandbox,
    DockerSandbox,
    MockSandbox,
    create_sandbox,
)

logger = logging.getLogger(__name__)

MAX_OUTPUT_DISPLAY_CHARS = 5_000


class TestRunStore:
    """In-memory thread-safe store for test execution runs."""

    __test__ = False

    def __init__(self, max_runs: int = 100):
        self._runs: Dict[str, TestRunResponse] = {}
        self._max_runs = max_runs

    def save_run(self, run_id: str, response: TestRunResponse) -> None:
        if len(self._runs) >= self._max_runs:
            # Pop oldest run
            oldest_key = next(iter(self._runs))
            self._runs.pop(oldest_key, None)
        self._runs[run_id] = response

    def get_run(self, run_id: str) -> Optional[TestRunResponse]:
        return self._runs.get(run_id)


# Global singleton store for runs
test_run_store = TestRunStore()


class TestRunner:
    """Orchestrates test validation, ephemeral environment staging, execution, and reporting."""

    __test__ = False

    def __init__(self, sandbox: Optional[BaseSandbox] = None):
        self._sandbox_override = sandbox

    @staticmethod
    def validate_request_parameters(request: TestRunRequest) -> None:
        """Validate input parameters before workspace preparation or cloning."""
        if request.timeout_seconds < 1 or request.timeout_seconds > 60:
            raise RequestValidationError(
                f"Invalid timeout {request.timeout_seconds}s. Timeout must be between 1 and 60 seconds."
            )

        raw_test_file = request.test_file.strip()
        if not raw_test_file:
            raise RequestValidationError("test_file parameter must not be empty.")

        test_p = Path(raw_test_file)
        if test_p.is_absolute() or raw_test_file.startswith("/") or raw_test_file.startswith("\\"):
            raise RequestValidationError("Absolute paths are not allowed for test_file.")

        if ".." in test_p.parts:
            raise RequestValidationError("Path traversal sequences ('..') are strictly prohibited.")

        if test_p.suffix.lower() != ".py":
            raise RequestValidationError(
                f"Unsupported test file extension '{test_p.suffix}'. Only Python (.py) files are supported."
            )

        if request.test_code:
            try:
                ast.parse(request.test_code)
            except SyntaxError as syn_err:
                raise RequestValidationError(
                    f"Supplied test_code contains invalid Python syntax: {syn_err.msg} (line {syn_err.lineno})"
                ) from syn_err

        if request.target_file:
            raw_target = request.target_file.strip()
            target_p = Path(raw_target)
            if target_p.is_absolute() or raw_target.startswith("/") or ".." in target_p.parts:
                raise RequestValidationError("Invalid target_file path or path traversal detected.")
            if target_p.suffix.lower() != ".py":
                raise RequestValidationError("Target file for coverage must be a Python (.py) file.")

    def validate_request(
        self,
        request: TestRunRequest,
        repo_path: Path,
    ) -> Tuple[Path, Optional[Path]]:
        """Validate test execution request against security constraints and workspace.

        Args:
            request: TestRunRequest.
            repo_path: Base directory of the cloned repository.

        Returns:
            Tuple of (resolved_test_file_path, optional_resolved_target_file_path).

        Raises:
            RequestValidationError: When path traversal, invalid timeout, or bad extensions are detected.
            FileNotFoundError: When the test file does not exist (and test_code was not supplied).
        """
        # Validate parameter semantics
        TestRunner.validate_request_parameters(request)

        raw_test_file = request.test_file.strip()
        test_p = Path(raw_test_file)
        resolved_test = (repo_path / test_p).resolve()
        try:
            resolved_test.relative_to(repo_path.resolve())
        except ValueError as exc:
            raise RequestValidationError(
                "Security violation: test_file path escapes repository workspace boundary."
            ) from exc

        # If test_code is not supplied, file must already exist in repo
        if not request.test_code and not resolved_test.is_file():
            raise FileNotFoundError(
                f"Test file '{raw_test_file}' not found in repository."
            )

        # If test_code is supplied, validate AST syntax before executing
        if request.test_code:
            try:
                ast.parse(request.test_code)
            except SyntaxError as syn_err:
                raise RequestValidationError(
                    f"Supplied test_code contains invalid Python syntax: {syn_err.msg} (line {syn_err.lineno})"
                ) from syn_err

        # 3. Target file validation for coverage (optional)
        resolved_target: Optional[Path] = None
        if request.target_file:
            raw_target = request.target_file.strip()
            target_p = Path(raw_target)
            if target_p.is_absolute() or raw_target.startswith("/") or ".." in target_p.parts:
                raise RequestValidationError("Invalid target_file path or path traversal detected.")
            if target_p.suffix.lower() != ".py":
                raise RequestValidationError("Target file for coverage must be a Python (.py) file.")

            resolved_target = (repo_path / target_p).resolve()
            try:
                resolved_target.relative_to(repo_path.resolve())
            except ValueError as exc:
                raise RequestValidationError(
                    "Security violation: target_file path escapes repository workspace boundary."
                ) from exc

            if not resolved_target.is_file():
                logger.warning("Target file for coverage '%s' does not exist in repo.", raw_target)
                resolved_target = None

        return resolved_test, resolved_target

    async def run_tests(
        self,
        request: TestRunRequest,
        repo_path: Path,
        repo_info: RepositoryInfo,
    ) -> TestRunResponse:
        """Run approved pytest tests in an isolated sandbox and report results.

        Args:
            request: TestRunRequest parameters.
            repo_path: Cloned repository directory.
            repo_info: Repository metadata.

        Returns:
            TestRunResponse containing test summary, results, coverage, and logs.
        """
        run_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        # 1. Validate request
        resolved_test_file, resolved_target_file = self.validate_request(request, repo_path)

        # 2. Determine sandbox
        if self._sandbox_override:
            sandbox = self._sandbox_override
        else:
            try:
                sandbox = create_sandbox(allow_mock=request.allow_mock)
            except SandboxUnavailableError as exc:
                logger.warning("Test run %s rejected: %s", run_id, exc)
                response = TestRunResponse(
                    run_id=run_id,
                    status="failed_to_start",
                    test_file=request.test_file,
                    target_file=request.target_file,
                    summary=TestSummary(),
                    test_results=[],
                    duration_seconds=0.0,
                    exit_code=None,
                    coverage=None,
                    sandbox=DockerSandbox().get_info(),
                    execution_type="none",
                    stdout="",
                    stderr=str(exc),
                    error_message=str(exc),
                    warnings=[
                        "Container execution unavailable: Docker runtime is required to safely run untrusted code.",
                        "To simulate execution without Docker, enable allow_mock in test run request.",
                    ],
                    created_at=created_at,
                )
                test_run_store.save_run(run_id, response)
                return response

        sandbox_info = sandbox.get_info()
        execution_type = sandbox_info.sandbox_type if sandbox_info.sandbox_type in ("container", "mocked") else ("mocked" if isinstance(sandbox, MockSandbox) else "container")

        # 3. Create disposable, isolated copy of repository workspace
        # Original repository remains completely untouched!
        disposable_workspace = Path(tempfile.mkdtemp(prefix="repopilot_test_run_")).resolve()

        try:
            # Copy repo contents (excluding VCS and cached files)
            def _ignore_patterns(path, names):
                return {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache"}

            shutil.copytree(repo_path, disposable_workspace, dirs_exist_ok=True, ignore=_ignore_patterns)

            # If inline test_code was provided, write it into the disposable copy
            test_file_rel = str(resolved_test_file.relative_to(repo_path.resolve()))
            dest_test_file = disposable_workspace / test_file_rel
            if request.test_code:
                dest_test_file.parent.mkdir(parents=True, exist_ok=True)
                dest_test_file.write_text(request.test_code, encoding="utf-8")

            # 4. Construct fixed, controlled command (NO user input command construction)
            cov_report_file = ".coverage_report.json"
            pytest_cmd = ["pytest", test_file_rel, "-v", "--tb=short"]

            if request.coverage:
                cov_scope = "."
                if resolved_target_file:
                    target_rel = str(resolved_target_file.relative_to(repo_path.resolve()))
                    # Use directory or module name for coverage scope
                    cov_scope = str(Path(target_rel).parent) or "."

                pytest_cmd.extend([
                    f"--cov={cov_scope}",
                    f"--cov-report=json:{cov_report_file}",
                ])

            # 5. Execute in isolated sandbox
            exec_result = await sandbox.run(
                workdir=disposable_workspace,
                command=pytest_cmd,
                timeout_seconds=request.timeout_seconds,
            )

            # 6. Parse pytest output
            summary, test_results, warnings = TestReporter.parse_output(
                stdout=exec_result.stdout,
                stderr=exec_result.stderr,
                exit_code=exec_result.exit_code,
                repo_root=disposable_workspace,
            )

            # 7. Parse coverage report if requested
            coverage_report: Optional[CoverageReport] = None
            if request.coverage:
                cov_path = disposable_workspace / cov_report_file
                target_rel_str = str(resolved_target_file.relative_to(repo_path.resolve())) if resolved_target_file else request.target_file
                coverage_report = CoverageParser.parse_file(
                    report_path=cov_path,
                    repo_root=disposable_workspace,
                    target_file=target_rel_str,
                )

            # 8. Determine overall status
            if exec_result.timed_out:
                status = "timed_out"
            elif exec_result.error:
                status = "failed_to_start"
            elif exec_result.exit_code == 0:
                status = "completed"
            elif summary.failed > 0:
                status = "completed"  # completed with test failures
            elif summary.errors > 0 or exec_result.exit_code != 0:
                status = "failed"
            else:
                status = "completed"

            # Add mock warning if running in mock sandbox
            if isinstance(sandbox, MockSandbox):
                warnings.append(
                    "Simulated Execution Notice: Test results were produced in a mock environment "
                    "because Docker container execution is not configured on this host. Real sandbox execution has not occurred."
                )

            # Build and store response
            response = TestRunResponse(
                run_id=run_id,
                status=status,
                test_file=request.test_file,
                target_file=request.target_file,
                summary=summary,
                test_results=test_results,
                duration_seconds=exec_result.duration_seconds,
                exit_code=exec_result.exit_code,
                coverage=coverage_report,
                sandbox=sandbox_info,
                execution_type=execution_type,
                stdout=exec_result.stdout[:MAX_OUTPUT_DISPLAY_CHARS],
                stderr=exec_result.stderr[:MAX_OUTPUT_DISPLAY_CHARS],
                error_message=exec_result.error,
                warnings=warnings,
                created_at=created_at,
            )

            test_run_store.save_run(run_id, response)
            return response

        finally:
            # 9. Clean up disposable workspace immediately
            try:
                shutil.rmtree(disposable_workspace, ignore_errors=True)
            except Exception as rm_err:
                logger.debug("Failed to clean up disposable workspace %s: %s", disposable_workspace, rm_err)
