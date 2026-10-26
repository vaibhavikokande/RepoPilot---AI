"""Evidence and context collector for AI code review."""

import ast
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from app.code_intelligence.models import CodeFile
from app.code_quality.metrics import (
    calculate_generic_nesting_depth,
    calculate_js_ts_cyclomatic_complexity,
    calculate_python_cyclomatic_complexity,
    calculate_python_nesting_depth,
)
from app.code_quality.models import EntityQualityMetrics
from app.code_quality.rules import QualityRulesEngine
from app.code_review.models import (
    CodeReviewFinding,
    EvidenceContext,
    ReviewTargetNotFoundError,
    ReviewValidationError,
)
from app.security_analysis.rules import SecurityRulesEngine

logger = logging.getLogger(__name__)

MAX_REVIEW_LINES = 600
MAX_REVIEW_CHARS = 24_000


class EvidenceCollector:
    """Validates files and gathers source code, structural entities, and static checks."""

    def __init__(
        self,
        quality_rules: Optional[QualityRulesEngine] = None,
        security_rules: Optional[SecurityRulesEngine] = None,
    ):
        self.quality_rules = quality_rules or QualityRulesEngine()
        self.security_rules = security_rules or SecurityRulesEngine()

    def validate_and_resolve_path(self, repo_path: Path, file_path: str) -> Path:
        """Validate file path against path traversal and repository boundaries.

        Args:
            repo_path: Cloned repository root path.
            file_path: Relative path supplied by user.

        Returns:
            Resolved absolute Path.

        Raises:
            ReviewValidationError: For traversal or malformed paths.
            ReviewTargetNotFoundError: If file does not exist.
        """
        raw = file_path.strip()
        if not raw:
            raise ReviewValidationError("file_path parameter must not be empty.")

        path_obj = Path(raw)
        if path_obj.is_absolute() or raw.startswith("/") or raw.startswith("\\"):
            raise ReviewValidationError("Absolute paths are not permitted for code review.")

        if ".." in path_obj.parts:
            raise ReviewValidationError("Path traversal sequences ('..') are strictly prohibited.")

        resolved = (repo_path / path_obj).resolve()
        try:
            resolved.relative_to(repo_path.resolve())
        except ValueError as exc:
            raise ReviewValidationError(
                "Security violation: file path escapes repository workspace boundary."
            ) from exc

        if not resolved.is_file():
            raise ReviewTargetNotFoundError(f"Source file '{raw}' not found in repository.")

        return resolved

    def collect(
        self,
        repo_path: Path,
        file_path: str,
        entity_name: Optional[str] = None,
        review_focus: str = "all",
    ) -> EvidenceContext:
        """Collect source code, line ranges, and deterministic quality/security findings.

        Args:
            repo_path: Root repository directory.
            file_path: Target file path.
            entity_name: Optional specific function or class to focus on.
            review_focus: Review focus filter.

        Returns:
            EvidenceContext populated with source evidence and deterministic findings.
        """
        resolved_file = self.validate_and_resolve_path(repo_path, file_path)
        content = resolved_file.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        start_line = 1
        end_line = total_lines
        target_entity_type = None

        # Python structural discovery
        functions: List[str] = []
        classes: List[str] = []
        imports: List[str] = []
        parsed_ast: Optional[ast.AST] = None

        if resolved_file.suffix.lower() == ".py":
            try:
                parsed_ast = ast.parse(content)
                for node in ast.walk(parsed_ast):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(node.name)
                        if entity_name and node.name == entity_name:
                            start_line = node.lineno
                            end_line = getattr(node, "end_lineno", node.lineno)
                            target_entity_type = "function"
                    elif isinstance(node, ast.ClassDef):
                        classes.append(node.name)
                        if entity_name and node.name == entity_name:
                            start_line = node.lineno
                            end_line = getattr(node, "end_lineno", node.lineno)
                            target_entity_type = "class"
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        mod = node.module or ""
                        for alias in node.names:
                            imports.append(f"{mod}.{alias.name}")
            except SyntaxError as exc:
                logger.debug("Python AST parsing failed for %s: %s", file_path, exc)

        if entity_name and target_entity_type is None:
            # Check non-python or fallback regex
            found = False
            for idx, line in enumerate(lines, 1):
                if f"def {entity_name}" in line or f"function {entity_name}" in line or f"class {entity_name}" in line:
                    start_line = idx
                    end_line = min(total_lines, idx + 50)
                    target_entity_type = "entity"
                    found = True
                    break
            if not found:
                raise ReviewTargetNotFoundError(
                    f"Target entity '{entity_name}' was not found in file '{file_path}'."
                )

        # Slice relevant lines for review
        # Clamp start and end line
        start_line = max(1, min(start_line, total_lines))
        end_line = max(start_line, min(end_line, total_lines))

        selected_lines = lines[start_line - 1 : end_line]
        # Format line-numbered string: " 15 | def foo():"
        numbered_lines_list = [
            f"{start_line + i:4d} | {line}" for i, line in enumerate(selected_lines)
        ]
        numbered_text = "\n".join(numbered_lines_list)

        # Enforce maximum character payload limit
        if len(numbered_text) > MAX_REVIEW_CHARS:
            numbered_text = numbered_text[:MAX_REVIEW_CHARS] + "\n... [Remaining lines truncated for context limits]"

        # Collect deterministic static analysis findings
        static_quality_findings: List[CodeReviewFinding] = []
        static_security_findings: List[CodeReviewFinding] = []

        # 1. Deterministic code quality checks
        static_quality_findings = self._collect_quality_findings(
            repo_path=repo_path,
            file_path=file_path,
            resolved_file=resolved_file,
            content=content,
            lines=lines,
            parsed_ast=parsed_ast,
            target_entity=entity_name,
        )

        # 2. Deterministic security checks
        static_security_findings = self._collect_security_findings(
            repo_path=repo_path,
            file_path=file_path,
            resolved_file=resolved_file,
            content=content,
            parsed_ast=parsed_ast,
        )

        return EvidenceContext(
            file_path=file_path,
            absolute_path=str(resolved_file),
            content="\n".join(selected_lines),
            total_lines=total_lines,
            start_line=start_line,
            end_line=end_line,
            entity_name=entity_name,
            entity_type=target_entity_type,
            numbered_lines=numbered_text,
            classes=classes,
            functions=functions,
            imports=imports,
            static_quality_findings=static_quality_findings,
            static_security_findings=static_security_findings,
        )

    def _collect_quality_findings(
        self,
        repo_path: Path,
        file_path: str,
        resolved_file: Path,
        content: str,
        lines: List[str],
        parsed_ast: Optional[ast.AST],
        target_entity: Optional[str] = None,
    ) -> List[CodeReviewFinding]:
        """Run deterministic quality rules and convert into CodeReviewFinding."""
        findings: List[CodeReviewFinding] = []
        counter = 1

        if resolved_file.suffix.lower() == ".py" and parsed_ast:
            for node in ast.walk(parsed_ast):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if target_entity and node.name != target_entity:
                        continue
                    end_lineno = getattr(node, "end_lineno", node.lineno)
                    fn_lines = max(1, end_lineno - node.lineno + 1)
                    snippet = "\n".join(lines[node.lineno - 1 : end_lineno])

                    complexity = calculate_python_cyclomatic_complexity(node)
                    nesting = calculate_python_nesting_depth(node)
                    has_doc = bool(ast.get_docstring(node))
                    param_count = len(node.args.args)

                    metrics = EntityQualityMetrics(
                        entity_name=node.name,
                        entity_type="function",
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=end_lineno,
                        lines_count=fn_lines,
                        cyclomatic_complexity=complexity,
                        max_nesting_depth=nesting,
                        parameter_count=param_count,
                        has_docstring=has_doc,
                    )

                    q_findings = self.quality_rules.check_entity_metrics(metrics)
                    for qf in q_findings:
                        # Extract first line of function as evidence
                        first_line = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                        findings.append(
                            CodeReviewFinding(
                                finding_id=f"cr_static_qual_{counter}",
                                title=qf.rule_name,
                                category="maintainability",
                                severity=qf.severity.value,
                                confidence="high",
                                file_path=file_path,
                                start_line=node.lineno,
                                end_line=end_lineno,
                                entity_name=node.name,
                                problem=qf.message,
                                evidence=first_line,
                                recommendation=qf.suggestion or "Refactor function to reduce complexity and length.",
                                source="static_analysis",
                                is_verified=True,
                            )
                        )
                        counter += 1

                # Check broad exceptions
                elif isinstance(node, ast.ExceptHandler):
                    if node.type is None or (isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException")):
                        ev_line = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "except Exception:"
                        findings.append(
                            CodeReviewFinding(
                                finding_id=f"cr_static_qual_{counter}",
                                title="Overly Broad Exception Handling",
                                category="correctness",
                                severity="medium",
                                confidence="high",
                                file_path=file_path,
                                start_line=node.lineno,
                                end_line=getattr(node, "end_lineno", node.lineno),
                                problem="Catching broad Exception can mask critical programming bugs and system errors.",
                                evidence=ev_line,
                                recommendation="Catch specific exceptions instead (e.g. ValueError, KeyError, OSError).",
                                source="static_analysis",
                                is_verified=True,
                            )
                        )
                        counter += 1

        return findings

    def _collect_security_findings(
        self,
        repo_path: Path,
        file_path: str,
        resolved_file: Path,
        content: str,
        parsed_ast: Optional[ast.AST],
    ) -> List[CodeReviewFinding]:
        """Run deterministic security rules and convert into CodeReviewFinding."""
        findings: List[CodeReviewFinding] = []
        counter = 1

        sec_findings = []
        if resolved_file.suffix.lower() == ".py" and parsed_ast:
            sec_findings = self.security_rules.analyze_python_ast(
                tree=parsed_ast,
                file_path=file_path,
                source_code=content,
            )
        elif resolved_file.suffix.lower() in (".js", ".jsx", ".ts", ".tsx"):
            sec_findings = self.security_rules.analyze_js_ts_source(
                file_path=file_path,
                source_code=content,
            )

        for sf in sec_findings:
            findings.append(
                CodeReviewFinding(
                    finding_id=f"cr_static_sec_{counter}",
                    title=sf.title,
                    category="security",
                    severity=sf.severity.value,
                    confidence=sf.confidence.value,
                    file_path=file_path,
                    start_line=sf.start_line,
                    end_line=sf.end_line,
                    entity_name=sf.entity_name,
                    problem=sf.description,
                    evidence=sf.evidence_summary,
                    recommendation=sf.remediation,
                    source="static_analysis",
                    is_verified=True,
                )
            )
            counter += 1

        return findings
