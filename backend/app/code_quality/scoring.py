"""Repository health scoring and grade calculation engine."""

import logging
from typing import Dict, List, Tuple

from app.code_quality.models import (
    FindingCategory,
    FindingSeverity,
    HealthScoreBreakdown,
    QualityFinding,
)

logger = logging.getLogger(__name__)


def calculate_letter_grade(score: float) -> str:
    """Map a 0-100 score to a letter grade (A, B, C, D, F)."""
    if score >= 90.0:
        return "A"
    elif score >= 80.0:
        return "B"
    elif score >= 70.0:
        return "C"
    elif score >= 60.0:
        return "D"
    else:
        return "F"


def calculate_health_scores(
    findings: List[QualityFinding],
    total_lines: int,
    total_entities: int,
    documented_entities: int,
    parse_errors_count: int = 0,
) -> HealthScoreBreakdown:
    """Compute sub-scores (0-100) and overall repository health score and letter grade.

    Penalties are normalized by codebase volume (in KLOC = 1,000 lines) so larger codebases
    are not disproportionately penalized for having more total code.
    """
    # Scale factor: roughly 1 KLOC minimum
    kloc = max(1.0, total_lines / 1000.0)

    # 1. Maintainability Sub-Score
    maint_penalties = 0.0
    # 2. Complexity Sub-Score
    complexity_penalties = 0.0
    # 3. Reliability Sub-Score
    reliability_penalties = 0.0

    for f in findings:
        severity_weight = {
            FindingSeverity.CRITICAL: 15.0,
            FindingSeverity.ERROR: 8.0,
            FindingSeverity.WARNING: 3.0,
            FindingSeverity.INFO: 1.0,
        }.get(f.severity, 2.0)

        if f.category in (FindingCategory.SIZE, FindingCategory.MAINTAINABILITY):
            maint_penalties += severity_weight
        elif f.category == FindingCategory.COMPLEXITY:
            complexity_penalties += severity_weight
        elif f.category in (FindingCategory.ERROR_HANDLING, FindingCategory.DUPLICATION):
            reliability_penalties += severity_weight

    # Additional penalty for unparseable files
    reliability_penalties += parse_errors_count * 10.0

    # Normalize penalties by KLOC with diminishing returns
    norm_maint_penalty = (maint_penalties / kloc) * 1.5
    norm_complexity_penalty = (complexity_penalties / kloc) * 1.8
    norm_reliability_penalty = (reliability_penalties / kloc) * 1.5

    maintainability_score = round(max(0.0, min(100.0, 100.0 - norm_maint_penalty)), 1)
    complexity_score = round(max(0.0, min(100.0, 100.0 - norm_complexity_penalty)), 1)
    reliability_score = round(max(0.0, min(100.0, 100.0 - norm_reliability_penalty)), 1)

    # Documentation Score: based on docstring coverage
    if total_entities == 0:
        documentation_score = 100.0
    else:
        doc_ratio = documented_entities / total_entities
        documentation_score = round(doc_ratio * 100.0, 1)

    # Weighted Composite Overall Score
    overall_score = round(
        (0.35 * maintainability_score)
        + (0.30 * complexity_score)
        + (0.15 * documentation_score)
        + (0.20 * reliability_score),
        1,
    )

    letter_grade = calculate_letter_grade(overall_score)

    return HealthScoreBreakdown(
        maintainability_score=maintainability_score,
        complexity_score=complexity_score,
        documentation_score=documentation_score,
        reliability_score=reliability_score,
        overall_score=overall_score,
        letter_grade=letter_grade,
    )


def calculate_file_health_score(
    findings: List[QualityFinding],
    total_lines: int,
) -> Tuple[float, str]:
    """Calculate health score (0-100) and letter grade for an individual file."""
    penalty = 0.0
    for f in findings:
        if f.severity == FindingSeverity.CRITICAL:
            penalty += 20.0
        elif f.severity == FindingSeverity.ERROR:
            penalty += 12.0
        elif f.severity == FindingSeverity.WARNING:
            penalty += 5.0
        elif f.severity == FindingSeverity.INFO:
            penalty += 1.5

    # Scale slightly by file size so small files with one warning aren't crushed
    scale = max(0.5, min(2.0, total_lines / 100.0))
    adjusted_penalty = penalty / scale

    score = round(max(0.0, min(100.0, 100.0 - adjusted_penalty)), 1)
    grade = calculate_letter_grade(score)
    return score, grade
