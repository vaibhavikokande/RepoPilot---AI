"""Sandbox isolation manager for test execution.

Enforces execution inside a secure, unprivileged container with network disabled,
memory/CPU/PID limits, and zero access to host environment or secrets.
"""

import asyncio
import logging
import os
import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional

from app.schemas.test_execution import SandboxInfo, SandboxStatus
from app.test_execution.models import (
    SandboxExecutionResult,
    SandboxUnavailableError,
)

logger = logging.getLogger(__name__)

DEFAULT_RUNNER_IMAGE = "python:3.11-slim"
MAX_OUTPUT_BYTES = 50_000  # 50 KB maximum output captured from container


class BaseSandbox(ABC):
    """Abstract base class for test execution sandbox environments."""

    @abstractmethod
    async def run(
        self,
        workdir: Path,
        command: List[str],
        timeout_seconds: int,
    ) -> SandboxExecutionResult:
        """Execute a controlled command within the isolated sandbox."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check whether the sandbox runtime is ready on this host."""

    @abstractmethod
    def get_info(self) -> SandboxInfo:
        """Return metadata describing the sandbox configuration."""


class DockerSandbox(BaseSandbox):
    """Container-based isolated execution sandbox using Docker.

    Security constraints applied:
    - Non-root user (--user 1000:1000)
    - Disabled network (--network none)
    - Dropped capabilities (--cap-drop=ALL)
    - Security option (--security-opt=no-new-privileges)
    - Read/write access restricted to the ephemeral disposable workspace only
    - Strict memory (512MB), CPU (1.0 core), and PID (64) limits
    - Strict execution timeout
    - Zero inheritance of host environment variables or secrets
    - Automatic container removal (--rm)
    """

    def __init__(self, image: str = DEFAULT_RUNNER_IMAGE):
        self.image = image
        self.docker_bin = shutil.which("docker")

    def is_available(self) -> bool:
        """Return True if docker binary is present in system PATH."""
        return self.docker_bin is not None

    def get_info(self) -> SandboxInfo:
        return SandboxInfo(
            sandbox_type="docker",
            is_isolated=True,
            network_disabled=True,
            non_root=True,
            resource_limits={
                "memory": "512m",
                "cpus": "1.0",
                "pids": 64,
            },
            runner_image=self.image,
        )

    async def run(
        self,
        workdir: Path,
        command: List[str],
        timeout_seconds: int,
    ) -> SandboxExecutionResult:
        """Run command inside an isolated Docker container with zero network access."""
        if not self.is_available():
            raise SandboxUnavailableError(
                "Docker container runtime is not available on this server. "
                "Untrusted code execution requires containerized isolation."
            )

        resolved_workdir = Path(workdir).resolve()
        start_time = time.time()

        # Build hardened docker run arguments
        docker_cmd = [
            str(self.docker_bin),
            "run",
            "--rm",
            "--network", "none",
            "--user", "1000:1000",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--memory=512m",
            "--cpus=1.0",
            "--pids-limit=64",
            "-v", f"{resolved_workdir}:/workspace:rw",
            "-w", "/workspace",
            "-e", "PYTHONPATH=.",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-e", "PYTHONUNBUFFERED=1",
            self.image,
        ] + command

        logger.info(
            "Executing sandboxed test command in Docker container: %s (timeout: %ds)",
            command,
            timeout_seconds,
        )

        try:
            # We explicitly pass an empty or clean env dictionary to create_subprocess_exec
            # so the parent process's environment variables (e.g. OPENAI_API_KEY) are not passed
            safe_host_env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            }

            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=safe_host_env,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=float(timeout_seconds),
                )
                duration = time.time() - start_time

                stdout = stdout_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]
                stderr = stderr_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_BYTES]

                return SandboxExecutionResult(
                    exit_code=process.returncode or 0,
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=round(duration, 3),
                    timed_out=False,
                )

            except asyncio.TimeoutError:
                duration = time.time() - start_time
                logger.warning("Docker sandbox command timed out after %ds", timeout_seconds)
                try:
                    process.kill()
                    await process.wait()
                except Exception as kill_err:
                    logger.debug("Error while terminating timed-out container process: %s", kill_err)

                return SandboxExecutionResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"Execution timed out after {timeout_seconds} seconds.",
                    duration_seconds=round(duration, 3),
                    timed_out=True,
                    error=f"Test run exceeded maximum execution limit of {timeout_seconds}s.",
                )

        except Exception as exc:
            duration = time.time() - start_time
            logger.error("Failed to run command in Docker sandbox: %s", exc)
            return SandboxExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=str(exc),
                duration_seconds=round(duration, 3),
                timed_out=False,
                error=f"Failed to start Docker sandbox: {str(exc)}",
            )


class MockSandbox(BaseSandbox):
    """Deterministic mock sandbox for offline testing, CI, and local verification.

    Simulates realistic pytest execution and coverage output without executing
    arbitrary code on the host machine.
    """

    def __init__(
        self,
        default_exit_code: int = 0,
        mock_stdout: Optional[str] = None,
        mock_stderr: str = "",
        simulate_timeout: bool = False,
    ):
        self.default_exit_code = default_exit_code
        self.mock_stdout = mock_stdout
        self.mock_stderr = mock_stderr
        self.simulate_timeout = simulate_timeout

    def is_available(self) -> bool:
        return True

    def get_info(self) -> SandboxInfo:
        return SandboxInfo(
            sandbox_type="mock",
            is_isolated=True,
            network_disabled=True,
            non_root=True,
            resource_limits={"mock_mode": True},
            runner_image="mock-runner:latest",
        )

    async def run(
        self,
        workdir: Path,
        command: List[str],
        timeout_seconds: int,
    ) -> SandboxExecutionResult:
        """Simulate sandboxed pytest execution."""
        start_time = time.time()
        await asyncio.sleep(0.05)  # simulate brief execution delay

        if self.simulate_timeout:
            return SandboxExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution timed out after {timeout_seconds} seconds (mock).",
                duration_seconds=float(timeout_seconds),
                timed_out=True,
                error="Test run timed out in mock sandbox.",
            )

        # Check if pytest is running on a real test file in workdir
        test_file_arg = command[1] if len(command) > 1 else "test_target.py"
        full_test_path = workdir / test_file_arg

        if self.mock_stdout is not None:
            stdout = self.mock_stdout
            exit_code = self.default_exit_code
        elif full_test_path.is_file():
            # Generate grounded mock pytest output based on the file content
            content = full_test_path.read_text(encoding="utf-8", errors="replace")
            # Count test functions in the test file
            test_funcs = [
                line.strip().split("(")[0].replace("def ", "")
                for line in content.splitlines()
                if line.strip().startswith("def test_")
            ]
            if not test_funcs:
                test_funcs = ["test_example"]

            passed_lines = "\n".join([f"{test_file_arg}::{f} PASSED" for f in test_funcs])
            stdout = (
                f"============================= test session starts ==============================\n"
                f"platform linux -- Python 3.11.8, pytest-8.1.1\n"
                f"collected {len(test_funcs)} items\n\n"
                f"{passed_lines}\n\n"
                f"============================== {len(test_funcs)} passed in 0.12s ==============================="
            )
            exit_code = 0
        else:
            stdout = (
                f"============================= test session starts ==============================\n"
                f"platform linux -- Python 3.11.8, pytest-8.1.1\n"
                f"collected 2 items\n\n"
                f"{test_file_arg}::test_happy_path PASSED\n"
                f"{test_file_arg}::test_edge_case PASSED\n\n"
                f"============================== 2 passed in 0.15s ==============================="
            )
            exit_code = 0

        # If coverage was requested in command, simulate a mock coverage.json file in workdir
        for arg in command:
            if "--cov-report=json:" in arg:
                report_rel_path = arg.split("--cov-report=json:")[1]
                cov_file = workdir / report_rel_path
                mock_cov_json = (
                    '{"meta": {"format": 3, "version": "7.4.4"}, '
                    '"files": {"app/services/example.py": {"executed_lines": [1, 2, 3, 5, 6], '
                    '"missing_lines": [8, 9], "summary": {"covered_lines": 5, "num_statements": 7, '
                    '"percent_covered": 71.42857142857143, "missing_lines": 2}}}, '
                    '"totals": {"covered_lines": 5, "num_statements": 7, "percent_covered": 71.42857142857143, '
                    '"missing_lines": 2}}'
                )
                try:
                    cov_file.write_text(mock_cov_json, encoding="utf-8")
                except Exception as write_err:
                    logger.debug("Failed to write mock coverage file: %s", write_err)

        duration = time.time() - start_time
        return SandboxExecutionResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=self.mock_stderr,
            duration_seconds=round(duration, 3),
            timed_out=False,
        )


def get_sandbox_status() -> SandboxStatus:
    """Return diagnostic status of container sandbox runtime on the server."""
    docker_bin = shutil.which("docker")
    requirements = [
        "Docker runtime engine available in system PATH",
        "Non-root unprivileged container user (UID 1000:1000)",
        "Zero network egress (--network none)",
        "Resource constraints: 512MB RAM, 1.0 CPU core, 64 PIDs",
        "Ephemeral disposable workspace mounted read/write; zero host secret inheritance",
        "Strict execution timeout enforcement (max 60 seconds)",
    ]

    if docker_bin is None:
        return SandboxStatus(
            available=False,
            sandbox_type="docker",
            configured=False,
            message=(
                "Container sandbox runtime (Docker) is not installed or available in system PATH. "
                "Real execution of untrusted code is safely disabled to protect host integrity. "
                "To enable safe execution, install and start Docker."
            ),
            requirements=requirements,
        )

    return SandboxStatus(
        available=True,
        sandbox_type="docker",
        configured=True,
        message="Docker container sandbox is available for isolated test execution.",
        requirements=requirements,
    )


def create_sandbox(allow_mock: bool = False) -> BaseSandbox:
    """Factory creating appropriate sandbox instance or raising if unavailable.

    Args:
        allow_mock: If True, returns MockSandbox when Docker is unavailable.

    Returns:
        BaseSandbox instance (DockerSandbox or MockSandbox).

    Raises:
        SandboxUnavailableError: When Docker is missing and allow_mock is False.
    """
    docker_sandbox = DockerSandbox()
    if docker_sandbox.is_available():
        return docker_sandbox

    if allow_mock:
        logger.info("Docker unavailable; using MockSandbox per request configuration.")
        return MockSandbox()

    raise SandboxUnavailableError(
        "Sandbox execution unavailable: Docker container runtime is not detected on the server. "
        "Host security policy strictly prohibits executing untrusted repository code directly in the backend process. "
        "To enable containerized test isolation, install and run Docker."
    )
