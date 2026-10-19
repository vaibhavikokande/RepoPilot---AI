"""Validation engine for generated pytest code: checks syntax, structure, and test presence."""

import ast
import logging
from typing import List, Tuple

from app.schemas.test_generation import ValidationResult

logger = logging.getLogger(__name__)


class TestValidator:
    """Performs static syntax and structural validation on generated test code."""

    def validate(self, test_code: str) -> ValidationResult:
        """Validate generated test code for Python syntax and pytest structure.

        Args:
            test_code: Raw Python test code string.

        Returns:
            ValidationResult with syntax status, structure status, and detected test functions.
        """
        if not test_code or not test_code.strip():
            return ValidationResult(
                syntax_valid=False,
                structure_valid=False,
                test_functions_found=0,
                syntax_error="Generated test code is empty.",
                warnings=["The LLM returned empty test code."],
                execution_status="not_run",
            )

        # 1. AST Syntax validation
        try:
            tree = ast.parse(test_code)
            syntax_valid = True
            syntax_error = None
        except SyntaxError as exc:
            logger.info("Syntax validation failed for generated test code: %s", exc)
            return ValidationResult(
                syntax_valid=False,
                structure_valid=False,
                test_functions_found=0,
                syntax_error=f"SyntaxError on line {exc.lineno}: {exc.msg}",
                warnings=["Code does not parse as valid Python."],
                execution_status="not_run",
            )
        except Exception as exc:
            return ValidationResult(
                syntax_valid=False,
                structure_valid=False,
                test_functions_found=0,
                syntax_error=f"Parsing error: {exc}",
                warnings=["Unknown error during AST parsing."],
                execution_status="not_run",
            )

        # 2. Structural checks: discover test functions and classes
        test_functions_count, warnings = self._inspect_test_structure(tree)
        structure_valid = test_functions_count > 0

        if not structure_valid:
            warnings.append("No functions starting with 'test_' were found in the generated test code.")

        return ValidationResult(
            syntax_valid=syntax_valid,
            structure_valid=structure_valid,
            test_functions_found=test_functions_count,
            syntax_error=syntax_error,
            warnings=warnings,
            execution_status="not_run",
        )

    def _inspect_test_structure(self, tree: ast.AST) -> Tuple[int, List[str]]:
        """Walk AST to find test functions, pytest imports, and potential warnings."""
        test_functions = 0
        has_pytest_import = False
        warnings: List[str] = []

        for node in ast.walk(tree):
            # Check for pytest import
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ("pytest", "unittest"):
                        has_pytest_import = True
            elif isinstance(node, ast.ImportFrom):
                if node.module in ("pytest", "unittest", "unittest.mock"):
                    has_pytest_import = True

            # Count test functions and test methods
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    test_functions += 1

        if not has_pytest_import:
            warnings.append("No explicit 'pytest' import was detected in the generated code.")

        return test_functions, warnings
