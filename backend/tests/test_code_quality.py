"""Unit and integration tests for Day 7 Code Quality Analysis and Health Scoring."""

import ast
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.code_intelligence.models import CodeEntity, CodeFile, CodeImport
from app.code_quality import (
    CodeQualityAnalyzer,
    CodeQualityRequest,
    CodeQualityResponse,
    EntityQualityMetrics,
    FindingCategory,
    FindingSeverity,
    QualityFinding,
    QualityRulesEngine,
    calculate_file_health_score,
    calculate_generic_nesting_depth,
    calculate_health_scores,
    calculate_js_ts_cyclomatic_complexity,
    calculate_letter_grade,
    calculate_python_cyclomatic_complexity,
    calculate_python_nesting_depth,
    count_file_lines,
    find_duplicate_blocks,
)
from app.schemas.repository import RepositoryInfo
from app.services.repository_service import RepositoryAccessError, RepositoryCloningError

client = TestClient(app)


class TestMetricsCalculation:
    """Tests for line counting, cyclomatic complexity, nesting depth, and code duplication."""

    def test_count_file_lines_python(self):
        sample_code = (
            "# A module comment\n"
            "\n"
            "def add(a, b):\n"
            '    """Add two numbers."""\n'
            "    return a + b\n"
        )
        counts = count_file_lines(sample_code, "python")
        assert counts["total"] == 5
        assert counts["blank"] == 1
        assert counts["comment"] >= 1  # includes # comment and docstring line
        assert counts["code"] >= 2

    def test_count_file_lines_javascript(self):
        sample_code = (
            "// Comment line\n"
            "/* Block comment */\n"
            "\n"
            "function greet(name) {\n"
            "  return `Hello ${name}`;\n"
            "}\n"
        )
        counts = count_file_lines(sample_code, "javascript")
        assert counts["total"] == 6
        assert counts["blank"] == 1
        assert counts["comment"] == 2
        assert counts["code"] == 3

    def test_python_cyclomatic_complexity(self):
        code = (
            "def complex_func(x, y, z):\n"
            "    if x > 0 and y > 0:\n"  # if (+1) and (+1)
            "        for i in range(x):\n"  # for (+1)
            "            while z > 0:\n"  # while (+1)
            "                z -= 1\n"
            "    elif y < 0:\n"  # elif (+1)
            "        return False\n"
            "    return True\n"
        )
        tree = ast.parse(code)
        func_node = tree.body[0]
        complexity = calculate_python_cyclomatic_complexity(func_node)
        # Base 1 + if(1) + and(1) + for(1) + while(1) + elif(1) = 6
        assert complexity == 6

    def test_js_ts_cyclomatic_complexity(self):
        snippet = (
            "function check(a, b) {\n"
            "  if (a && b) {\n"
            "    for (let i = 0; i < 10; i++) {}\n"
            "  } else if (a || b) {\n"
            "    return false;\n"
            "  }\n"
            "  return true;\n"
            "}"
        )
        complexity = calculate_js_ts_cyclomatic_complexity(snippet)
        assert complexity >= 5

    def test_python_nesting_depth(self):
        code = (
            "def nested_func():\n"
            "    if True:\n"  # depth 1
            "        for i in range(5):\n"  # depth 2
            "            while False:\n"  # depth 3
            "                try:\n"  # depth 4
            "                    pass\n"
            "                except Exception:\n"
            "                    pass\n"
        )
        tree = ast.parse(code)
        func_node = tree.body[0]
        depth = calculate_python_nesting_depth(func_node)
        assert depth == 4

    def test_generic_nesting_depth(self):
        code = "function f() { if (true) { for (;;) { while (false) { pass; } } } }"
        depth = calculate_generic_nesting_depth(code)
        assert depth == 4

    def test_find_duplicate_blocks(self):
        block = (
            "    x = calculate_value(a, b)\n"
            "    y = process_intermediate(x)\n"
            "    result = format_output(y)\n"
            "    cache.store(result)\n"
            "    notifier.send(result)\n"
            "    return result\n"
        )
        file1 = f"def first():\n{block}"
        file2 = f"def second():\n{block}"

        dups = find_duplicate_blocks([("mod1.py", file1), ("mod2.py", file2)], min_lines=6)
        assert len(dups) >= 1
        assert dups[0]["file_path"] in ("mod1.py", "mod2.py")
        assert dups[0]["lines_count"] == 6


class TestQualityRules:
    """Tests for individual quality rule evaluation."""

    def test_file_length_rule(self):
        engine = QualityRulesEngine(file_len_warn=100, file_len_err=200)

        assert engine.check_file_length("small.py", 50) is None

        warn_finding = engine.check_file_length("medium.py", 120)
        assert warn_finding is not None
        assert warn_finding.severity == FindingSeverity.WARNING
        assert warn_finding.rule_id == "FILE_TOO_LARGE"

        err_finding = engine.check_file_length("large.py", 250)
        assert err_finding is not None
        assert err_finding.severity == FindingSeverity.ERROR

    def test_function_length_and_complexity_rules(self):
        engine = QualityRulesEngine(
            func_len_warn=20,
            func_len_err=50,
            complexity_warn=5,
            complexity_err=10,
            nesting_warn=2,
            nesting_err=3,
            param_warn=3,
        )

        metrics = EntityQualityMetrics(
            entity_name="heavy_routine",
            entity_type="function",
            file_path="service.py",
            start_line=10,
            end_line=45,
            lines_count=35,  # > func_len_warn
            cyclomatic_complexity=8,  # > complexity_warn
            max_nesting_depth=3,  # >= nesting_err
            parameter_count=4,  # >= param_warn
            has_docstring=False,
        )

        findings = engine.check_entity_metrics(metrics)
        rule_ids = {f.rule_id for f in findings}

        assert "FUNCTION_TOO_LONG" in rule_ids
        assert "HIGH_CYCLOMATIC_COMPLEXITY" in rule_ids
        assert "EXCESSIVE_NESTING" in rule_ids
        assert "TOO_MANY_PARAMETERS" in rule_ids
        assert "MISSING_DOCSTRING" in rule_ids

    def test_missing_docstring_ignores_private_methods(self):
        engine = QualityRulesEngine()
        metrics = EntityQualityMetrics(
            entity_name="_internal_helper",
            entity_type="function",
            file_path="service.py",
            start_line=1,
            end_line=5,
            lines_count=5,
            cyclomatic_complexity=1,
            max_nesting_depth=0,
            parameter_count=1,
            has_docstring=False,
        )
        findings = engine.check_entity_metrics(metrics)
        assert not any(f.rule_id == "MISSING_DOCSTRING" for f in findings)

    def test_broad_exception_rule(self):
        engine = QualityRulesEngine()
        code_swallow = (
            "try:\n"
            "    do_something()\n"
            "except Exception:\n"
            "    pass\n"
        )
        tree = ast.parse(code_swallow)
        findings = engine.check_python_broad_exceptions("app.py", tree)
        assert len(findings) == 1
        assert findings[0].rule_id == "BROAD_EXCEPTION"
        assert findings[0].severity == FindingSeverity.ERROR
        assert "Silent suppression" in findings[0].message

    def test_unused_import_rule(self):
        engine = QualityRulesEngine()
        imports = [
            CodeImport(
                module="os",
                imported_names=["path", "environ"],
                line_number=1,
                source_file="test.py",
            ),
            CodeImport(
                module="sys",
                imported_names=["argv"],
                line_number=2,
                source_file="test.py",
            ),
        ]
        # Only 'path' is used in the body, 'environ' and 'argv' are not
        source_code = (
            "from os import path, environ\n"
            "from sys import argv\n"
            "\n"
            "print(path.exists('/tmp'))\n"
        )
        findings = engine.check_potentially_unused_imports("test.py", imports, source_code)
        flagged_symbols = {f.entity_name for f in findings}

        assert "environ" in flagged_symbols
        assert "argv" in flagged_symbols
        assert "path" not in flagged_symbols


class TestHealthScoring:
    """Tests for health score calculations and letter grades."""

    def test_letter_grade_thresholds(self):
        assert calculate_letter_grade(95.0) == "A"
        assert calculate_letter_grade(90.0) == "A"
        assert calculate_letter_grade(85.0) == "B"
        assert calculate_letter_grade(75.0) == "C"
        assert calculate_letter_grade(65.0) == "D"
        assert calculate_letter_grade(45.0) == "F"

    def test_clean_codebase_scoring(self):
        breakdown = calculate_health_scores(
            findings=[],
            total_lines=1500,
            total_entities=10,
            documented_entities=10,
            parse_errors_count=0,
        )
        assert breakdown.overall_score == 100.0
        assert breakdown.letter_grade == "A"
        assert breakdown.maintainability_score == 100.0
        assert breakdown.documentation_score == 100.0

    def test_file_health_score(self):
        clean_score, clean_grade = calculate_file_health_score([], 100)
        assert clean_score == 100.0
        assert clean_grade == "A"

        bad_findings = [
            QualityFinding(
                id="1",
                rule_id="HIGH_COMPLEXITY",
                rule_name="High Complexity",
                category=FindingCategory.COMPLEXITY,
                severity=FindingSeverity.ERROR,
                file_path="test.py",
                start_line=1,
                end_line=10,
                message="Error",
                suggestion="Fix",
            )
        ]
        score, grade = calculate_file_health_score(bad_findings, 50)
        assert score < 100.0


class TestCodeQualityAnalyzer:
    """Integration test for full CodeQualityAnalyzer on a mock filesystem."""

    def test_analyzer_end_to_end(self, tmp_path):
        # Create a sample repo directory
        file_py = tmp_path / "module.py"
        file_py.write_text(
            '"""Module docstring."""\n'
            "import os\n"
            "\n"
            "def calculate_total(items, tax, discount, user, is_member, flag):\n"
            '    """Calculate total price."""\n'
            "    if items and tax > 0:\n"
            "        for item in items:\n"
            "            if item > 10:\n"
            "                pass\n"
            "    return 42\n"
            "\n"
            "def undocumented_func():\n"
            "    try:\n"
            "        pass\n"
            "    except Exception:\n"
            "        pass\n"
        )

        repo_info = RepositoryInfo(
            name="demo-repo",
            owner="tester",
            url="https://github.com/tester/demo-repo",
            default_branch="main",
        )

        analyzer = CodeQualityAnalyzer()
        response = analyzer.analyze_repository(tmp_path, repo_info)

        assert isinstance(response, CodeQualityResponse)
        assert response.status == "success"
        assert response.metrics.total_files_analyzed == 1
        assert response.metrics.total_functions == 2
        assert len(response.findings) >= 2  # too many params, broad exception, missing docstring, unused import

        rule_ids = {f.rule_id for f in response.findings}
        assert "BROAD_EXCEPTION" in rule_ids
        assert "TOO_MANY_PARAMETERS" in rule_ids
        assert "MISSING_DOCSTRING" in rule_ids
        assert "POTENTIALLY_UNUSED_IMPORT" in rule_ids

        assert len(response.file_summaries) == 1
        assert response.file_summaries[0].file_path == "module.py"
        assert response.health.overall_score <= 100.0


class TestCodeQualityAPIEndpoint:
    """Tests for POST /api/v1/repositories/quality endpoint."""

    def test_quality_invalid_url_rejected(self):
        response = client.post(
            "/api/v1/repositories/quality",
            json={"repository_url": "ftp://bad-url"},
        )
        assert response.status_code == 400
        assert "Only secure HTTPS URLs are permitted" in response.json()["detail"]

    @patch("app.api.v1.endpoints.repositories.CodeQualityAnalyzer.analyze_repository")
    @patch("app.services.repository_service.RepositoryService.cloned_repository")
    def test_quality_successful_flow(self, mock_clone, mock_analyze):
        mock_clone.return_value.__enter__.return_value = (Path("/fake/path"), "main")
        mock_analyze.return_value = CodeQualityResponse(
            repository=RepositoryInfo(
                name="Hello-World",
                owner="octocat",
                url="https://github.com/octocat/Hello-World",
                default_branch="main",
            ),
            health={
                "maintainability_score": 92.5,
                "complexity_score": 88.0,
                "documentation_score": 95.0,
                "reliability_score": 90.0,
                "overall_score": 91.2,
                "letter_grade": "A",
            },
            metrics={
                "total_lines": 500,
                "code_lines": 350,
                "comment_lines": 100,
                "blank_lines": 50,
                "total_files_analyzed": 5,
                "files_with_issues": 1,
                "total_functions": 8,
                "total_classes": 2,
                "average_function_length": 15.2,
                "average_cyclomatic_complexity": 2.4,
                "max_cyclomatic_complexity": 6,
                "docstring_coverage_percentage": 90.0,
                "duplicate_blocks_count": 0,
            },
            findings=[],
            file_summaries=[],
            category_breakdown={"complexity": 0, "size": 0},
            severity_breakdown={"critical": 0, "warning": 0},
            parsing_errors=[],
            status="success",
        )

        response = client.post(
            "/api/v1/repositories/quality",
            json={"repository_url": "https://github.com/octocat/Hello-World"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["health"]["overall_score"] == 91.2
        assert data["health"]["letter_grade"] == "A"
        assert data["metrics"]["total_files_analyzed"] == 5

    @patch("app.services.repository_service.RepositoryService.cloned_repository")
    def test_quality_repository_not_found(self, mock_clone):
        mock_clone.side_effect = RepositoryAccessError("Repository does not exist or is private")

        response = client.post(
            "/api/v1/repositories/quality",
            json={"repository_url": "https://github.com/octocat/private-repo"},
        )
        assert response.status_code == 404
        assert "Repository does not exist or is private" in response.json()["detail"]

    @patch("app.services.repository_service.RepositoryService.cloned_repository")
    def test_quality_cloning_error(self, mock_clone):
        mock_clone.side_effect = RepositoryCloningError("Failed to clone repository")

        response = client.post(
            "/api/v1/repositories/quality",
            json={"repository_url": "https://github.com/octocat/Hello-World"},
        )
        assert response.status_code == 502
        assert "Failed to clone repository" in response.json()["detail"]
