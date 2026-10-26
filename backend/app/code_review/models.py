"""Domain models, exceptions, and data containers for code review."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.schemas.code_review import (
    CodeReviewFinding,
    CodeReviewRequest,
    CodeReviewResponse,
    ReviewMetadata,
    ReviewSummary,
)


class CodeReviewError(Exception):
    """Base exception for code review errors."""


class ReviewValidationError(CodeReviewError):
    """Raised when review request parameters fail validation (e.g. path traversal)."""


class ReviewTargetNotFoundError(CodeReviewError):
    """Raised when target file or entity is not found in the repository."""


@dataclass
class EvidenceContext:
    """Collected evidence and context for the file/entity to be reviewed."""

    file_path: str
    absolute_path: str
    content: str
    total_lines: int
    start_line: int
    end_line: int
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    numbered_lines: str = ""
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    static_quality_findings: List[CodeReviewFinding] = field(default_factory=list)
    static_security_findings: List[CodeReviewFinding] = field(default_factory=list)
    related_chunks: List[str] = field(default_factory=list)


__all__ = [
    "CodeReviewError",
    "CodeReviewFinding",
    "CodeReviewRequest",
    "CodeReviewResponse",
    "EvidenceContext",
    "ReviewMetadata",
    "ReviewSummary",
    "ReviewTargetNotFoundError",
    "ReviewValidationError",
]
