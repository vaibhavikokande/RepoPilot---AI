"""Domain models and exceptions for the AI debugging assistant."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.debug import (
    DebugRequest,
    DebugResponse,
    ParsedError,
    PossibleCause,
    SourceEvidence,
    StackFrame,
)


class DebugError(Exception):
    """Base exception for debugging assistant operations."""
    pass


class DebugValidationError(DebugError):
    """Raised when request payload or input data fails validation."""
    pass


class DebugSourceNotFoundError(DebugError):
    """Raised when a referenced source file is not found in the repository."""
    pass


class DebugExecutionError(DebugError):
    """Raised when an internal error occurs during debugging analysis."""
    pass


class RetrievedContext(BaseModel):
    """Container for all source evidence and context retrieved for debugging."""

    evidence_items: List[SourceEvidence] = Field(default_factory=list)
    related_files: List[str] = Field(default_factory=list)
    missing_files: List[str] = Field(default_factory=list)
    context_text: str = Field("", description="Formatted context text for LLM prompt")
    total_lines: int = Field(0)
    has_exact_source: bool = Field(False)
