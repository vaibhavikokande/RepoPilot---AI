"""Severity and confidence level definitions, ordering, and classification helpers."""

from typing import Dict
from app.schemas.security import SecurityConfidence, SecuritySeverity

# Sorting rank: lower index = higher priority in display
SEVERITY_ORDER: Dict[SecuritySeverity, int] = {
    SecuritySeverity.CRITICAL: 0,
    SecuritySeverity.HIGH: 1,
    SecuritySeverity.MEDIUM: 2,
    SecuritySeverity.LOW: 3,
    SecuritySeverity.INFORMATIONAL: 4,
}

CONFIDENCE_ORDER: Dict[SecurityConfidence, int] = {
    SecurityConfidence.HIGH: 0,
    SecurityConfidence.MEDIUM: 1,
    SecurityConfidence.LOW: 2,
}


def get_severity_rank(severity: SecuritySeverity) -> int:
    """Return numeric rank for sorting (0 is highest severity)."""
    return SEVERITY_ORDER.get(severity, 99)


def get_confidence_rank(confidence: SecurityConfidence) -> int:
    """Return numeric rank for sorting (0 is highest confidence)."""
    return CONFIDENCE_ORDER.get(confidence, 99)


def is_actionable_vulnerability(severity: SecuritySeverity) -> bool:
    """Determine whether finding requires immediate triage (Critical or High)."""
    return severity in (SecuritySeverity.CRITICAL, SecuritySeverity.HIGH)
