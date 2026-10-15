"""Reporting, categorization, summary aggregation, and deduplication for security findings."""

from typing import Dict, List, Set, Tuple

from app.schemas.security import (
    SecurityFinding,
    SecuritySeverity,
    SecuritySummary,
)
from app.security_analysis.severity import get_confidence_rank, get_severity_rank


def calculate_security_summary(findings: List[SecurityFinding]) -> SecuritySummary:
    """Aggregate finding counts by severity.

    Args:
        findings: List of SecurityFinding items.

    Returns:
        SecuritySummary model with total and per-severity counts.
    """
    counts = {
        SecuritySeverity.CRITICAL: 0,
        SecuritySeverity.HIGH: 0,
        SecuritySeverity.MEDIUM: 0,
        SecuritySeverity.LOW: 0,
        SecuritySeverity.INFORMATIONAL: 0,
    }

    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    return SecuritySummary(
        critical=counts[SecuritySeverity.CRITICAL],
        high=counts[SecuritySeverity.HIGH],
        medium=counts[SecuritySeverity.MEDIUM],
        low=counts[SecuritySeverity.LOW],
        informational=counts[SecuritySeverity.INFORMATIONAL],
        total=len(findings),
    )


def calculate_category_summary(findings: List[SecurityFinding]) -> Dict[str, int]:
    """Aggregate finding counts by functional security category.

    Args:
        findings: List of SecurityFinding items.

    Returns:
        Dictionary mapping category names to integer counts.
    """
    cat_counts: Dict[str, int] = {}
    for finding in findings:
        cat_val = finding.category.value if hasattr(finding.category, "value") else str(finding.category)
        cat_counts[cat_val] = cat_counts.get(cat_val, 0) + 1
    return cat_counts


def deduplicate_and_sort_findings(findings: List[SecurityFinding]) -> List[SecurityFinding]:
    """Deduplicate findings sharing the same rule, file, and line, and sort by severity.

    Args:
        findings: Raw list of findings.

    Returns:
        Deduplicated and sorted list ordered by severity (Critical first), confidence, and file location.
    """
    seen_keys: Set[Tuple[str, str, int]] = set()
    deduped: List[SecurityFinding] = []

    for f in findings:
        key = (f.rule_id, f.file_path, f.start_line)
        if key not in seen_keys:
            seen_keys.add(key)
            deduped.append(f)

    # Sort: Severity rank (0 is critical), then confidence rank, then file path, then line number
    deduped.sort(
        key=lambda item: (
            get_severity_rank(item.severity),
            get_confidence_rank(item.confidence),
            item.file_path,
            item.start_line,
        )
    )

    return deduped


def generate_deterministic_security_summary(
    summary: SecuritySummary,
    category_summary: Dict[str, int],
    repo_name: str,
) -> str:
    """Generate a concise executive summary paragraph for reports."""
    if summary.total == 0:
        return (
            f"Static security analysis of '{repo_name}' completed with 0 findings detected. "
            "No known security anti-patterns or hardcoded credential indicators were observed "
            "in supported source files."
        )

    critical_high = summary.critical + summary.high
    top_categories = sorted(category_summary.items(), key=lambda x: x[1], reverse=True)
    top_cat_names = [f"{k} ({v})" for k, v in top_categories[:3]]

    risk_tone = "high attention" if critical_high > 0 else "moderate maintainability review"

    return (
        f"Static security scan for '{repo_name}' identified {summary.total} finding(s) "
        f"({summary.critical} critical, {summary.high} high, {summary.medium} medium, "
        f"{summary.low} low, {summary.informational} informational), requiring {risk_tone}. "
        f"Primary areas of concern include: {', '.join(top_cat_names)}. "
        "All findings represent static code review indicators and require human verification."
    )
