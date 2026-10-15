"""Code quality analysis and repository health engine for RepoPilot AI."""

from app.code_quality.analyzer import CodeQualityAnalyzer
from app.code_quality.metrics import (
    calculate_generic_nesting_depth,
    calculate_js_ts_cyclomatic_complexity,
    calculate_python_cyclomatic_complexity,
    calculate_python_nesting_depth,
    count_file_lines,
    find_duplicate_blocks,
)
from app.code_quality.models import (
    CodeQualityRequest,
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
from app.code_quality.scoring import (
    calculate_file_health_score,
    calculate_health_scores,
    calculate_letter_grade,
)

__all__ = [
    "CodeQualityAnalyzer",
    "CodeQualityRequest",
    "CodeQualityResponse",
    "EntityQualityMetrics",
    "FileQualitySummary",
    "FindingCategory",
    "FindingSeverity",
    "HealthScoreBreakdown",
    "QualityFinding",
    "QualityRulesEngine",
    "RepositoryQualityMetrics",
    "calculate_file_health_score",
    "calculate_generic_nesting_depth",
    "calculate_health_scores",
    "calculate_js_ts_cyclomatic_complexity",
    "calculate_letter_grade",
    "calculate_python_cyclomatic_complexity",
    "calculate_python_nesting_depth",
    "count_file_lines",
    "find_duplicate_blocks",
]
