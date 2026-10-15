"""Code quality rule definitions, thresholds, and finding generators."""

import ast
import re
from typing import Dict, List, Optional, Set, Tuple

from app.code_intelligence.models import CodeEntity, CodeFile, CodeImport
from app.code_quality.models import (
    EntityQualityMetrics,
    FindingCategory,
    FindingSeverity,
    QualityFinding,
)

# Configurable thresholds
FUNCTION_LENGTH_WARNING = 50
FUNCTION_LENGTH_ERROR = 100

FILE_LENGTH_WARNING = 400
FILE_LENGTH_ERROR = 800

NESTING_DEPTH_WARNING = 3
NESTING_DEPTH_ERROR = 4

CYCLOMATIC_COMPLEXITY_WARNING = 10
CYCLOMATIC_COMPLEXITY_ERROR = 15

PARAMETER_COUNT_WARNING = 5


class QualityRulesEngine:
    """Evaluates static quality rules across parsed files and code entities."""

    def __init__(
        self,
        func_len_warn: int = FUNCTION_LENGTH_WARNING,
        func_len_err: int = FUNCTION_LENGTH_ERROR,
        file_len_warn: int = FILE_LENGTH_WARNING,
        file_len_err: int = FILE_LENGTH_ERROR,
        nesting_warn: int = NESTING_DEPTH_WARNING,
        nesting_err: int = NESTING_DEPTH_ERROR,
        complexity_warn: int = CYCLOMATIC_COMPLEXITY_WARNING,
        complexity_err: int = CYCLOMATIC_COMPLEXITY_ERROR,
        param_warn: int = PARAMETER_COUNT_WARNING,
    ):
        self.func_len_warn = func_len_warn
        self.func_len_err = func_len_err
        self.file_len_warn = file_len_warn
        self.file_len_err = file_len_err
        self.nesting_warn = nesting_warn
        self.nesting_err = nesting_err
        self.complexity_warn = complexity_warn
        self.complexity_err = complexity_err
        self.param_warn = param_warn

    def check_file_length(self, file_path: str, total_lines: int) -> Optional[QualityFinding]:
        """Check if file length exceeds manageable thresholds."""
        if total_lines >= self.file_len_err:
            return QualityFinding(
                id=f"file_len_{hash(file_path)}_{total_lines}",
                rule_id="FILE_TOO_LARGE",
                rule_name="File Too Large",
                category=FindingCategory.SIZE,
                severity=FindingSeverity.ERROR,
                file_path=file_path,
                start_line=1,
                end_line=total_lines,
                message=f"File has {total_lines} lines (exceeds error threshold of {self.file_len_err} lines).",
                suggestion="Consider splitting this file into smaller, cohesive modules or subpackages.",
                metric_value=float(total_lines),
                threshold=float(self.file_len_err),
            )
        elif total_lines >= self.file_len_warn:
            return QualityFinding(
                id=f"file_len_{hash(file_path)}_{total_lines}",
                rule_id="FILE_TOO_LARGE",
                rule_name="File Too Large",
                category=FindingCategory.SIZE,
                severity=FindingSeverity.WARNING,
                file_path=file_path,
                start_line=1,
                end_line=total_lines,
                message=f"File has {total_lines} lines (exceeds warning threshold of {self.file_len_warn} lines).",
                suggestion="Monitor file growth and identify cohesive sections that could be extracted into separate modules.",
                metric_value=float(total_lines),
                threshold=float(self.file_len_warn),
            )
        return None

    def check_entity_metrics(
        self,
        metrics: EntityQualityMetrics,
    ) -> List[QualityFinding]:
        """Evaluate function/method quality metrics against thresholds."""
        findings: List[QualityFinding] = []

        # 1. Function / Method Length
        if metrics.lines_count >= self.func_len_err:
            findings.append(
                QualityFinding(
                    id=f"func_len_{hash(metrics.file_path)}_{metrics.start_line}",
                    rule_id="FUNCTION_TOO_LONG",
                    rule_name="Function Too Long",
                    category=FindingCategory.SIZE,
                    severity=FindingSeverity.ERROR,
                    file_path=metrics.file_path,
                    start_line=metrics.start_line,
                    end_line=metrics.end_line,
                    entity_name=metrics.entity_name,
                    entity_type=metrics.entity_type,
                    message=(
                        f"{metrics.entity_type.title()} '{metrics.entity_name}' spans {metrics.lines_count} lines "
                        f"(threshold: {self.func_len_err} lines)."
                    ),
                    suggestion="Decompose this function into smaller, single-responsibility helper functions.",
                    metric_value=float(metrics.lines_count),
                    threshold=float(self.func_len_err),
                )
            )
        elif metrics.lines_count >= self.func_len_warn:
            findings.append(
                QualityFinding(
                    id=f"func_len_{hash(metrics.file_path)}_{metrics.start_line}",
                    rule_id="FUNCTION_TOO_LONG",
                    rule_name="Function Too Long",
                    category=FindingCategory.SIZE,
                    severity=FindingSeverity.WARNING,
                    file_path=metrics.file_path,
                    start_line=metrics.start_line,
                    end_line=metrics.end_line,
                    entity_name=metrics.entity_name,
                    entity_type=metrics.entity_type,
                    message=(
                        f"{metrics.entity_type.title()} '{metrics.entity_name}' spans {metrics.lines_count} lines "
                        f"(threshold: {self.func_len_warn} lines)."
                    ),
                    suggestion="Consider refactoring long procedural blocks into focused helper routines.",
                    metric_value=float(metrics.lines_count),
                    threshold=float(self.func_len_warn),
                )
            )

        # 2. Cyclomatic Complexity
        if metrics.cyclomatic_complexity >= self.complexity_err:
            findings.append(
                QualityFinding(
                    id=f"complexity_{hash(metrics.file_path)}_{metrics.start_line}",
                    rule_id="HIGH_CYCLOMATIC_COMPLEXITY",
                    rule_name="High Cyclomatic Complexity",
                    category=FindingCategory.COMPLEXITY,
                    severity=FindingSeverity.ERROR,
                    file_path=metrics.file_path,
                    start_line=metrics.start_line,
                    end_line=metrics.end_line,
                    entity_name=metrics.entity_name,
                    entity_type=metrics.entity_type,
                    message=(
                        f"{metrics.entity_type.title()} '{metrics.entity_name}' has cyclomatic complexity of "
                        f"{metrics.cyclomatic_complexity} (threshold: {self.complexity_err})."
                    ),
                    suggestion=(
                        "Simplify branching by using lookup dictionaries, strategy objects, or early guard returns."
                    ),
                    metric_value=float(metrics.cyclomatic_complexity),
                    threshold=float(self.complexity_err),
                )
            )
        elif metrics.cyclomatic_complexity >= self.complexity_warn:
            findings.append(
                QualityFinding(
                    id=f"complexity_{hash(metrics.file_path)}_{metrics.start_line}",
                    rule_id="HIGH_CYCLOMATIC_COMPLEXITY",
                    rule_name="High Cyclomatic Complexity",
                    category=FindingCategory.COMPLEXITY,
                    severity=FindingSeverity.WARNING,
                    file_path=metrics.file_path,
                    start_line=metrics.start_line,
                    end_line=metrics.end_line,
                    entity_name=metrics.entity_name,
                    entity_type=metrics.entity_type,
                    message=(
                        f"{metrics.entity_type.title()} '{metrics.entity_name}' has cyclomatic complexity of "
                        f"{metrics.cyclomatic_complexity} (threshold: {self.complexity_warn})."
                    ),
                    suggestion="Reduce decision branching to improve readability and test coverage.",
                    metric_value=float(metrics.cyclomatic_complexity),
                    threshold=float(self.complexity_warn),
                )
            )

        # 3. Excessive Nesting Depth
        if metrics.max_nesting_depth >= self.nesting_err:
            findings.append(
                QualityFinding(
                    id=f"nesting_{hash(metrics.file_path)}_{metrics.start_line}",
                    rule_id="EXCESSIVE_NESTING",
                    rule_name="Excessive Nesting Depth",
                    category=FindingCategory.COMPLEXITY,
                    severity=FindingSeverity.ERROR,
                    file_path=metrics.file_path,
                    start_line=metrics.start_line,
                    end_line=metrics.end_line,
                    entity_name=metrics.entity_name,
                    entity_type=metrics.entity_type,
                    message=(
                        f"{metrics.entity_type.title()} '{metrics.entity_name}' has nesting depth of "
                        f"{metrics.max_nesting_depth} (threshold: {self.nesting_err})."
                    ),
                    suggestion="Invert conditional checks with guard clauses to return early and flatten code.",
                    metric_value=float(metrics.max_nesting_depth),
                    threshold=float(self.nesting_err),
                )
            )
        elif metrics.max_nesting_depth >= self.nesting_warn:
            findings.append(
                QualityFinding(
                    id=f"nesting_{hash(metrics.file_path)}_{metrics.start_line}",
                    rule_id="EXCESSIVE_NESTING",
                    rule_name="Excessive Nesting Depth",
                    category=FindingCategory.COMPLEXITY,
                    severity=FindingSeverity.WARNING,
                    file_path=metrics.file_path,
                    start_line=metrics.start_line,
                    end_line=metrics.end_line,
                    entity_name=metrics.entity_name,
                    entity_type=metrics.entity_type,
                    message=(
                        f"{metrics.entity_type.title()} '{metrics.entity_name}' has nesting depth of "
                        f"{metrics.max_nesting_depth} (threshold: {self.nesting_warn})."
                    ),
                    suggestion="Flatten nested loops or conditionals by extracting innermost logic.",
                    metric_value=float(metrics.max_nesting_depth),
                    threshold=float(self.nesting_warn),
                )
            )

        # 4. Parameter Count
        if metrics.parameter_count >= self.param_warn:
            findings.append(
                QualityFinding(
                    id=f"params_{hash(metrics.file_path)}_{metrics.start_line}",
                    rule_id="TOO_MANY_PARAMETERS",
                    rule_name="Too Many Parameters",
                    category=FindingCategory.MAINTAINABILITY,
                    severity=FindingSeverity.WARNING,
                    file_path=metrics.file_path,
                    start_line=metrics.start_line,
                    end_line=metrics.end_line,
                    entity_name=metrics.entity_name,
                    entity_type=metrics.entity_type,
                    message=(
                        f"{metrics.entity_type.title()} '{metrics.entity_name}' accepts {metrics.parameter_count} "
                        f"parameters (threshold: {self.param_warn})."
                    ),
                    suggestion="Group related parameters into a configuration object, dictionary, or data class.",
                    metric_value=float(metrics.parameter_count),
                    threshold=float(self.param_warn),
                )
            )

        # 5. Missing Docstring (for public functions/classes)
        if not metrics.has_docstring:
            is_private = metrics.entity_name.startswith("_") and not (
                metrics.entity_name.startswith("__") and metrics.entity_name.endswith("__")
            )
            # Only flag public entities
            if not is_private:
                findings.append(
                    QualityFinding(
                        id=f"doc_{hash(metrics.file_path)}_{metrics.start_line}",
                        rule_id="MISSING_DOCSTRING",
                        rule_name="Missing Documentation",
                        category=FindingCategory.DOCUMENTATION,
                        severity=FindingSeverity.INFO,
                        file_path=metrics.file_path,
                        start_line=metrics.start_line,
                        end_line=metrics.end_line,
                        entity_name=metrics.entity_name,
                        entity_type=metrics.entity_type,
                        message=f"Public {metrics.entity_type} '{metrics.entity_name}' has no docstring or documentation.",
                        suggestion="Add a docstring explaining the purpose, parameters, return value, and exceptions.",
                    )
                )

        return findings

    def check_python_broad_exceptions(
        self,
        file_path: str,
        tree: ast.AST,
    ) -> List[QualityFinding]:
        """Detect broad or swallowed exceptions (e.g. `except Exception:` with `pass`)."""
        findings: List[QualityFinding] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                is_broad = False
                handler_name = "broad exception"

                # Check bare except: or except BaseException: or except Exception:
                if node.type is None:
                    is_broad = True
                    handler_name = "bare 'except:'"
                elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                    is_broad = True
                    handler_name = f"'except {node.type.id}:'"

                if is_broad:
                    # Check if body is empty or just pass
                    is_empty_or_pass = False
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        is_empty_or_pass = True

                    severity = FindingSeverity.WARNING if not is_empty_or_pass else FindingSeverity.ERROR
                    msg = (
                        f"Silent suppression: {handler_name} caught with empty/pass body."
                        if is_empty_or_pass
                        else f"Broad exception handling: {handler_name} caught."
                    )
                    suggestion = (
                        "Catch specific exception types (e.g. ValueError, KeyError) and ensure errors are logged or handled."
                    )

                    findings.append(
                        QualityFinding(
                            id=f"exc_{hash(file_path)}_{node.lineno}",
                            rule_id="BROAD_EXCEPTION",
                            rule_name="Broad Exception Handling",
                            category=FindingCategory.ERROR_HANDLING,
                            severity=severity,
                            file_path=file_path,
                            start_line=node.lineno,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            message=msg,
                            suggestion=suggestion,
                        )
                    )

        return findings

    def check_potentially_unused_imports(
        self,
        file_path: str,
        imports: List[CodeImport],
        source_code: str,
    ) -> List[QualityFinding]:
        """Identify imported symbols that never appear in the file source body."""
        findings: List[QualityFinding] = []
        lines = source_code.splitlines()

        # Collect line numbers of import statements so we don't match occurrences on import lines themselves
        import_lines = {imp.line_number for imp in imports}
        non_import_code = "\n".join(
            line for i, line in enumerate(lines, 1) if i not in import_lines
        )

        for imp in imports:
            for name in imp.imported_names:
                # If imported as alias (e.g. import foo as bar), check alias
                symbol_to_check = imp.alias or name
                if symbol_to_check == "*":
                    continue

                # Search for whole word boundary
                pattern = rf"\b{re.escape(symbol_to_check)}\b"
                if not re.search(pattern, non_import_code):
                    findings.append(
                        QualityFinding(
                            id=f"unused_imp_{hash(file_path)}_{imp.line_number}_{symbol_to_check}",
                            rule_id="POTENTIALLY_UNUSED_IMPORT",
                            rule_name="Potentially Unused Import",
                            category=FindingCategory.MAINTAINABILITY,
                            severity=FindingSeverity.INFO,
                            file_path=file_path,
                            start_line=imp.line_number,
                            end_line=imp.line_number,
                            entity_name=symbol_to_check,
                            entity_type="import",
                            message=f"Imported symbol '{symbol_to_check}' is never referenced in this file.",
                            suggestion=f"Remove '{symbol_to_check}' from imports if unused.",
                        )
                    )

        return findings

    def check_duplicate_blocks(
        self,
        duplicate_hits: List[Dict[str, any]],
    ) -> List[QualityFinding]:
        """Convert duplicate block detection hits into quality findings."""
        findings: List[QualityFinding] = []

        for hit in duplicate_hits:
            file_path = hit["file_path"]
            start_line = hit["start_line"]
            end_line = hit["end_line"]
            orig_file = hit["original_file"]
            orig_start = hit["original_start"]
            lines_count = hit["lines_count"]

            findings.append(
                QualityFinding(
                    id=f"dup_{hash(file_path)}_{start_line}_{hash(orig_file)}",
                    rule_id="DUPLICATE_CODE_BLOCK",
                    rule_name="Duplicate Code Block",
                    category=FindingCategory.DUPLICATION,
                    severity=FindingSeverity.WARNING,
                    file_path=file_path,
                    start_line=start_line,
                    end_line=end_line,
                    message=(
                        f"Duplicate code block of {lines_count}+ lines matches code in "
                        f"'{orig_file}' (lines {orig_start}-{orig_start + lines_count - 1})."
                    ),
                    suggestion="Extract duplicate logic into a shared, reusable function or component.",
                    metric_value=float(lines_count),
                )
            )

        return findings
