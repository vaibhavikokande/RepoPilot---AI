"""Code quality analysis orchestrator: coordinates metrics, rule evaluation, and health scoring."""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.code_intelligence.models import CodeEntity, CodeFile, FileParseError
from app.code_quality.metrics import (
    calculate_generic_nesting_depth,
    calculate_js_ts_cyclomatic_complexity,
    calculate_python_cyclomatic_complexity,
    calculate_python_nesting_depth,
    count_file_lines,
    find_duplicate_blocks,
)
from app.code_quality.models import (
    CodeQualityResponse,
    EntityQualityMetrics,
    FileQualitySummary,
    FindingCategory,
    FindingSeverity,
    HealthScoreBreakdown,
    QualityFinding,
    RepositoryQualityMetrics,
)
from app.code_quality.rules import QualityRulesEngine
from app.code_quality.scoring import calculate_file_health_score, calculate_health_scores
from app.schemas.repository import RepositoryInfo

logger = logging.getLogger(__name__)


class CodeQualityAnalyzer:
    """Orchestrates comprehensive code quality and repository health analysis."""

    def __init__(
        self,
        intelligence_analyzer: Optional[Any] = None,
        rules_engine: Optional[QualityRulesEngine] = None,
    ):
        if intelligence_analyzer is not None:
            self.intelligence_analyzer = intelligence_analyzer
        else:
            from app.code_intelligence.analyzer import CodeIntelligenceAnalyzer
            self.intelligence_analyzer = CodeIntelligenceAnalyzer()

        self.rules_engine = rules_engine or QualityRulesEngine()

    def analyze_repository(
        self,
        repo_path: Path,
        repo_info: RepositoryInfo,
    ) -> CodeQualityResponse:
        """Run full code quality analysis across all supported files in a repository.

        Args:
            repo_path: Root Path of the cloned repository.
            repo_info: RepositoryInfo metadata.

        Returns:
            CodeQualityResponse with complete metrics, findings, and health grades.
        """
        repo_path = repo_path.resolve()
        logger.info("Starting code quality analysis for repository at %s", repo_path)

        # 1. Run static code intelligence to extract AST entities, imports, and file models
        _, files, _, _, _, parse_errors = self.intelligence_analyzer.analyze_repository(repo_path)

        all_findings: List[QualityFinding] = []
        file_summaries: List[FileQualitySummary] = []
        file_contents_for_duplication: List[Tuple[str, str]] = []

        total_lines_cum = 0
        code_lines_cum = 0
        comment_lines_cum = 0
        blank_lines_cum = 0

        total_functions_count = 0
        total_classes_count = 0
        function_lengths: List[int] = []
        function_complexities: List[int] = []
        documented_entities_count = 0
        total_public_entities_count = 0

        # 2. Analyze each code file
        for file in files:
            full_path = repo_path / file.path
            if not full_path.exists() or not full_path.is_file():
                continue

            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                logger.warning("Could not read file %s for quality analysis: %s", file.path, exc)
                continue

            file_contents_for_duplication.append((file.path, content))
            line_counts = count_file_lines(content, file.language)

            total_lines_cum += line_counts["total"]
            code_lines_cum += line_counts["code"]
            comment_lines_cum += line_counts["comment"]
            blank_lines_cum += line_counts["blank"]

            file_findings: List[QualityFinding] = []

            # Check file size rule
            file_len_finding = self.rules_engine.check_file_length(file.path, line_counts["total"])
            if file_len_finding:
                file_findings.append(file_len_finding)

            # Analyze entities per language
            lang = file.language.lower()
            file_func_count = 0
            file_class_count = 0
            file_complexities: List[int] = []

            if lang == "python":
                # Detailed Python AST-based metric evaluation
                try:
                    tree = ast.parse(content, filename=file.path)
                    # Check broad exceptions
                    exc_findings = self.rules_engine.check_python_broad_exceptions(file.path, tree)
                    file_findings.extend(exc_findings)

                    # Walk AST for function and class definitions
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            file_func_count += 1
                            total_functions_count += 1

                            entity_name = node.name
                            is_method = False  # heuristic; parent may be class
                            entity_type = "function"
                            start_l = node.lineno
                            end_l = getattr(node, "end_lineno", start_l)
                            length = max(1, end_l - start_l + 1)
                            function_lengths.append(length)

                            complexity = calculate_python_cyclomatic_complexity(node)
                            file_complexities.append(complexity)
                            function_complexities.append(complexity)

                            nesting = calculate_python_nesting_depth(node)
                            param_count = len(node.args.args)
                            has_doc = ast.get_docstring(node) is not None

                            is_public = not entity_name.startswith("_") or (
                                entity_name.startswith("__") and entity_name.endswith("__")
                            )
                            if is_public:
                                total_public_entities_count += 1
                                if has_doc:
                                    documented_entities_count += 1

                            metrics = EntityQualityMetrics(
                                entity_name=entity_name,
                                entity_type=entity_type,
                                file_path=file.path,
                                start_line=start_l,
                                end_line=end_l,
                                lines_count=length,
                                cyclomatic_complexity=complexity,
                                max_nesting_depth=nesting,
                                parameter_count=param_count,
                                has_docstring=has_doc,
                            )
                            file_findings.extend(self.rules_engine.check_entity_metrics(metrics))

                        elif isinstance(node, ast.ClassDef):
                            file_class_count += 1
                            total_classes_count += 1
                            has_doc = ast.get_docstring(node) is not None
                            is_public = not node.name.startswith("_")
                            if is_public:
                                total_public_entities_count += 1
                                if has_doc:
                                    documented_entities_count += 1

                            if not has_doc and is_public:
                                file_findings.append(
                                    QualityFinding(
                                        id=f"doc_{hash(file.path)}_{node.lineno}",
                                        rule_id="MISSING_DOCSTRING",
                                        rule_name="Missing Documentation",
                                        category=FindingCategory.DOCUMENTATION,
                                        severity=FindingSeverity.INFO,
                                        file_path=file.path,
                                        start_line=node.lineno,
                                        end_line=getattr(node, "end_lineno", node.lineno),
                                        entity_name=node.name,
                                        entity_type="class",
                                        message=f"Public class '{node.name}' has no docstring or documentation.",
                                        suggestion="Add a docstring explaining the class's purpose and responsibilities.",
                                    )
                                )

                except Exception as exc:
                    logger.debug("Python AST inspection fallback for %s: %s", file.path, exc)

            else:
                # JS, TS, or other language based on extracted entities from CodeFile
                lines = content.splitlines()
                for entity in file.entities:
                    if entity.type in ("function", "method"):
                        file_func_count += 1
                        total_functions_count += 1
                        length = max(1, entity.end_line - entity.start_line + 1)
                        function_lengths.append(length)

                        snippet_lines = lines[entity.start_line - 1 : entity.end_line]
                        snippet = "\n".join(snippet_lines)

                        complexity = calculate_js_ts_cyclomatic_complexity(snippet)
                        file_complexities.append(complexity)
                        function_complexities.append(complexity)

                        nesting = calculate_generic_nesting_depth(snippet)
                        param_count = len(entity.parameters)
                        has_doc = bool(entity.docstring)

                        is_public = not entity.name.startswith("_")
                        if is_public:
                            total_public_entities_count += 1
                            if has_doc:
                                documented_entities_count += 1

                        metrics = EntityQualityMetrics(
                            entity_name=entity.name,
                            entity_type=entity.type,
                            file_path=file.path,
                            start_line=entity.start_line,
                            end_line=entity.end_line,
                            lines_count=length,
                            cyclomatic_complexity=complexity,
                            max_nesting_depth=nesting,
                            parameter_count=param_count,
                            has_docstring=has_doc,
                        )
                        file_findings.extend(self.rules_engine.check_entity_metrics(metrics))

                    elif entity.type == "class":
                        file_class_count += 1
                        total_classes_count += 1
                        has_doc = bool(entity.docstring)
                        is_public = not entity.name.startswith("_")
                        if is_public:
                            total_public_entities_count += 1
                            if has_doc:
                                documented_entities_count += 1

                        if not has_doc and is_public:
                            file_findings.append(
                                QualityFinding(
                                    id=f"doc_{hash(file.path)}_{entity.start_line}",
                                    rule_id="MISSING_DOCSTRING",
                                    rule_name="Missing Documentation",
                                    category=FindingCategory.DOCUMENTATION,
                                    severity=FindingSeverity.INFO,
                                    file_path=file.path,
                                    start_line=entity.start_line,
                                    end_line=entity.end_line,
                                    entity_name=entity.name,
                                    entity_type="class",
                                    message=f"Public class '{entity.name}' has no docstring or documentation.",
                                    suggestion="Add a documentation comment explaining this class's role.",
                                )
                            )

            # Check unused imports
            unused_import_findings = self.rules_engine.check_potentially_unused_imports(
                file.path, file.imports, content
            )
            file_findings.extend(unused_import_findings)

            # Calculate individual file health score
            file_score, file_grade = calculate_file_health_score(file_findings, line_counts["total"])

            avg_comp = (
                round(sum(file_complexities) / len(file_complexities), 1)
                if file_complexities
                else 1.0
            )
            max_comp = max(file_complexities) if file_complexities else 1

            file_summaries.append(
                FileQualitySummary(
                    file_path=file.path,
                    language=file.language,
                    total_lines=line_counts["total"],
                    code_lines=line_counts["code"],
                    comment_lines=line_counts["comment"],
                    blank_lines=line_counts["blank"],
                    functions_count=file_func_count,
                    classes_count=file_class_count,
                    average_complexity=avg_comp,
                    max_complexity=max_comp,
                    findings_count=len(file_findings),
                    health_score=file_score,
                    letter_grade=file_grade,
                )
            )

            all_findings.extend(file_findings)

        # 3. Detect duplicate code blocks across files
        duplicate_hits = find_duplicate_blocks(file_contents_for_duplication, min_lines=6)
        duplication_findings = self.rules_engine.check_duplicate_blocks(duplicate_hits)
        all_findings.extend(duplication_findings)

        # 4. Sort findings deterministically by severity (CRITICAL -> ERROR -> WARNING -> INFO)
        severity_order = {
            FindingSeverity.CRITICAL: 0,
            FindingSeverity.ERROR: 1,
            FindingSeverity.WARNING: 2,
            FindingSeverity.INFO: 3,
        }
        all_findings.sort(key=lambda f: (severity_order.get(f.severity, 4), f.file_path, f.start_line))

        # 5. Compute global metrics
        avg_func_len = (
            round(sum(function_lengths) / len(function_lengths), 1)
            if function_lengths
            else 0.0
        )
        avg_complexity = (
            round(sum(function_complexities) / len(function_complexities), 1)
            if function_complexities
            else 1.0
        )
        max_complexity = max(function_complexities) if function_complexities else 1
        doc_coverage = (
            round((documented_entities_count / total_public_entities_count) * 100.0, 1)
            if total_public_entities_count > 0
            else 100.0
        )

        files_with_issues = len({f.file_path for f in all_findings})

        repo_metrics = RepositoryQualityMetrics(
            total_lines=total_lines_cum,
            code_lines=code_lines_cum,
            comment_lines=comment_lines_cum,
            blank_lines=blank_lines_cum,
            total_files_analyzed=len(files),
            files_with_issues=files_with_issues,
            total_functions=total_functions_count,
            total_classes=total_classes_count,
            average_function_length=avg_func_len,
            average_cyclomatic_complexity=avg_complexity,
            max_cyclomatic_complexity=max_complexity,
            docstring_coverage_percentage=doc_coverage,
            duplicate_blocks_count=len(duplicate_hits),
        )

        # 6. Calculate composite health scores and letter grade
        health_breakdown = calculate_health_scores(
            findings=all_findings,
            total_lines=total_lines_cum,
            total_entities=total_public_entities_count,
            documented_entities=documented_entities_count,
            parse_errors_count=len(parse_errors),
        )

        # 7. Category and severity breakdown counts
        category_breakdown: Dict[str, int] = {}
        for cat in FindingCategory:
            category_breakdown[cat.value] = sum(1 for f in all_findings if f.category == cat)

        severity_breakdown: Dict[str, int] = {}
        for sev in FindingSeverity:
            severity_breakdown[sev.value] = sum(1 for f in all_findings if f.severity == sev)

        # Sort file summaries by health score ascending (files needing most attention first)
        file_summaries.sort(key=lambda s: (s.health_score, -s.findings_count))

        logger.info(
            "Quality analysis complete: %d findings, health score %.1f (%s)",
            len(all_findings),
            health_breakdown.overall_score,
            health_breakdown.letter_grade,
        )

        return CodeQualityResponse(
            repository=repo_info,
            health=health_breakdown,
            metrics=repo_metrics,
            findings=all_findings,
            file_summaries=file_summaries,
            category_breakdown=category_breakdown,
            severity_breakdown=severity_breakdown,
            parsing_errors=parse_errors,
            status="success",
        )
