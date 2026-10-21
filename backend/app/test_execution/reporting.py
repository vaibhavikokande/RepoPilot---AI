"""Reporting and normalization module for test execution outcomes."""

import re
from pathlib import Path
from typing import List, Optional, Tuple

from app.schemas.test_execution import TestCaseResult, TestSummary

# Regex patterns for pytest line outcomes
# e.g., tests/test_calc.py::test_add PASSED [ 50%]
PYTEST_NODE_PATTERN = re.compile(
    r"^(?P<node>[^\s]+::(?P<name>[^\s]+))\s+(?P<status>PASSED|FAILED|SKIPPED|ERROR)",
    re.MULTILINE,
)

# Regex pattern for pytest summary footer
# e.g., = 2 passed, 1 failed, 1 skipped in 0.45s =
SUMMARY_PATTERN = re.compile(
    r"=\s*(?:(?P<passed>\d+)\s+passed)?(?:,?\s*(?P<failed>\d+)\s+failed)?(?:,?\s*(?P<skipped>\d+)\s+skipped)?(?:,?\s*(?P<errors>\d+)\s+error(?:s)?)?",
)

# Regex for collection errors
COLLECTION_ERROR_PATTERN = re.compile(
    r"(?:ERROR collecting|CollectionError:|ImportError:|ModuleNotFoundError:)\s*(?P<msg>[^\n]+)",
)

# Regex for missing dependencies
MISSING_MODULE_PATTERN = re.compile(
    r"No module named\s+['\"](?P<mod>[^'\"]+)['\"]",
)


class TestReporter:
    """Normalizes raw pytest console output into structured summaries and test cases."""

    __test__ = False

    @staticmethod
    def parse_output(
        stdout: str,
        stderr: str,
        exit_code: int,
        repo_root: Optional[Path] = None,
    ) -> Tuple[TestSummary, List[TestCaseResult], List[str]]:
        """Parse pytest stdout and stderr to extract test summary and individual results.

        Args:
            stdout: Raw stdout string from pytest run.
            stderr: Raw stderr string from pytest run.
            exit_code: Pytest process exit code.
            repo_root: Optional repository root for path sanitization.

        Returns:
            Tuple of (TestSummary, List[TestCaseResult], List[str] warnings).
        """
        combined = f"{stdout}\n{stderr}"
        sanitized = TestReporter.sanitize_text(combined, repo_root)

        test_results: List[TestCaseResult] = []
        warnings: List[str] = []

        # 1. Parse individual test node outcomes
        for match in PYTEST_NODE_PATTERN.finditer(sanitized):
            node_name = match.group("name") or match.group("node")
            status_raw = match.group("status").lower()

            test_results.append(
                TestCaseResult(
                    name=node_name,
                    status=status_raw,
                    duration_seconds=0.0,
                    message=None,
                )
            )

        # 2. Extract summary counts from the pytest footer line
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        error_count = 0

        for line in reversed(sanitized.splitlines()):
            line_str = line.strip()
            if line_str.startswith("=") and ("passed" in line_str or "failed" in line_str or "error" in line_str or "skipped" in line_str):
                p_m = re.search(r"(\d+)\s+passed", line_str)
                f_m = re.search(r"(\d+)\s+failed", line_str)
                s_m = re.search(r"(\d+)\s+skipped", line_str)
                e_m = re.search(r"(\d+)\s+error", line_str)

                if p_m:
                    passed_count = int(p_m.group(1))
                if f_m:
                    failed_count = int(f_m.group(1))
                if s_m:
                    skipped_count = int(s_m.group(1))
                if e_m:
                    error_count = int(e_m.group(1))
                break
        else:
            # Fallback to tallying from parsed node results
            for tr in test_results:
                if tr.status == "passed":
                    passed_count += 1
                elif tr.status == "failed":
                    failed_count += 1
                elif tr.status == "skipped":
                    skipped_count += 1
                elif tr.status == "error":
                    error_count += 1

        # 3. Detect collection errors or missing module imports
        for match in COLLECTION_ERROR_PATTERN.finditer(sanitized):
            err_msg = match.group(0).strip()
            if err_msg not in warnings:
                warnings.append(err_msg)
            if error_count == 0 and failed_count == 0:
                error_count += 1

        mod_match = MISSING_MODULE_PATTERN.search(sanitized)
        if mod_match:
            missing_pkg = mod_match.group("mod")
            dep_warning = (
                f"Missing dependency '{missing_pkg}': The repository requires packages not included "
                "in the base runner. RepoPilot does not automatically install unvetted packages."
            )
            if dep_warning not in warnings:
                warnings.append(dep_warning)

        total_count = passed_count + failed_count + skipped_count + error_count
        if total_count == 0 and len(test_results) > 0:
            total_count = len(test_results)

        # 4. Handle exit code edge cases
        if exit_code == 5 and total_count == 0:
            warnings.append("Pytest collected 0 tests in the specified test file.")
        elif exit_code != 0 and total_count == 0:
            error_count = max(error_count, 1)
            total_count = error_count

        summary = TestSummary(
            total=total_count,
            passed=passed_count,
            failed=failed_count,
            skipped=skipped_count,
            errors=error_count,
        )

        return summary, test_results, warnings

    @staticmethod
    def sanitize_text(text: str, repo_root: Optional[Path] = None) -> str:
        """Sanitize output by removing server paths, workspace absolute paths, and secrets."""
        cleaned = text

        # Strip /workspace/ container paths
        cleaned = cleaned.replace("/workspace/", "")

        # Strip host repository root if provided
        if repo_root:
            cleaned = cleaned.replace(str(repo_root), "")

        # Strip generic temporary directory paths
        cleaned = re.sub(r"/tmp/repopilot_[a-zA-Z0-9_\-]+/?", "", cleaned)
        cleaned = re.sub(r"/var/folders/[^\s]+", "", cleaned)

        # Redact potential sensitive tokens (e.g. sk-..., bearer tokens)
        cleaned = re.sub(r"sk-[a-zA-Z0-9]{20,}", "[REDACTED_API_KEY]", cleaned)
        cleaned = re.sub(r"ghp_[a-zA-Z0-9]{20,}", "[REDACTED_GITHUB_TOKEN]", cleaned)

        return cleaned
