"""Domain models and Pydantic schemas for AI debugging assistant."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class StackFrame(BaseModel):
    """A single frame extracted from a stack trace."""

    file_path: Optional[str] = Field(None, description="File path from the stack frame")
    line_number: Optional[int] = Field(None, description="Line number from the stack frame")
    function_name: Optional[str] = Field(None, description="Function or method name")
    code_context: Optional[str] = Field(None, description="Code snippet from the stack frame if available")
    is_application_code: bool = Field(True, description="Whether this frame is from user application vs stdlib/vendor")


class ParsedError(BaseModel):
    """Structured information extracted from an error message or stack trace."""

    error_type: Optional[str] = Field(None, description="Exception or error class (e.g. 'TypeError', 'ReferenceError')")
    error_message: str = Field("", description="The core error message text")
    language: Optional[str] = Field(None, description="Detected or specified programming language")
    frames: List[StackFrame] = Field(default_factory=list, description="Extracted stack frames, most recent last")
    file_paths: List[str] = Field(default_factory=list, description="All file paths mentioned in the error")
    raw_trace: str = Field("", description="Original raw error/trace text (truncated to safety limit)")


class SourceEvidence(BaseModel):
    """A relevant source code snippet retrieved from the repository."""

    file_path: str = Field(..., description="Repository-relative file path")
    start_line: int = Field(..., description="1-indexed starting line")
    end_line: int = Field(..., description="1-indexed ending line")
    code_snippet: str = Field(..., description="Relevant source code lines")
    entity_name: Optional[str] = Field(None, description="Function, class, or method name if known")
    relevance: str = Field("", description="Brief explanation of why this source is relevant")


class PossibleCause(BaseModel):
    """A ranked hypothesis about what may be causing the error."""

    rank: int = Field(..., description="Rank (1 = most likely)")
    title: str = Field(..., description="Short description of the hypothesized cause")
    explanation: str = Field(..., description="Detailed reasoning with evidence references")
    confidence: str = Field("medium", description="Confidence: 'high', 'medium', 'low'")
    supporting_evidence: List[str] = Field(
        default_factory=list,
        description="List of evidence references or files supporting this hypothesis",
    )


class DebugRequest(BaseModel):
    """Request payload for debugging analysis."""

    repository_url: str = Field(..., description="Public GitHub repository URL (https://github.com/owner/repo)")
    error_message: str = Field(
        ...,
        description="Error message, stack trace, or exception output to analyze",
        min_length=1,
        max_length=15000,
    )
    reproduction_steps: Optional[str] = Field(
        None,
        description="Optional steps to reproduce the error",
        max_length=5000,
    )
    expected_behavior: Optional[str] = Field(
        None,
        description="Optional description of what was expected to happen",
        max_length=3000,
    )
    file_path: Optional[str] = Field(
        None,
        description="Optional specific file path to focus analysis on",
        max_length=500,
    )
    language: Optional[str] = Field(
        None,
        description="Optional language hint (e.g. 'python', 'javascript')",
        max_length=50,
    )


class DebugResponse(BaseModel):
    """Structured debugging analysis response."""

    debug_id: str = Field(..., description="Unique debugging session identifier")
    repository: RepositoryInfo = Field(..., description="Repository metadata")
    error_type: Optional[str] = Field(None, description="Identified error/exception type")
    error_summary: str = Field(..., description="Plain-language explanation of what the error means")
    root_cause: str = Field(..., description="Most likely root cause explanation based on available evidence")
    confidence: str = Field("medium", description="Overall confidence in the diagnosis: 'high', 'medium', 'low'")
    confidence_note: str = Field(
        "Confidence represents the assistant's assessment based on static analysis of available code and stack trace evidence, not a guarantee.",
        description="Disclaimer about confidence meaning",
    )
    evidence: List[SourceEvidence] = Field(
        default_factory=list,
        description="Relevant source code evidence from the repository",
    )
    related_files: List[str] = Field(
        default_factory=list,
        description="Repository-relative paths of files related to the error",
    )
    possible_causes: List[PossibleCause] = Field(
        default_factory=list,
        description="Ranked hypotheses about error causes",
    )
    recommended_steps: List[str] = Field(
        default_factory=list,
        description="Ordered list of practical debugging steps",
    )
    suggested_fix: Optional[str] = Field(
        None,
        description="Suggested code fix when evidence strongly supports one (read-only, not automatically applied)",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Information that would improve the diagnosis or confirm hypotheses",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Known constraints of this static analysis",
    )
    parsed_error: ParsedError = Field(..., description="Structured extraction from the input error/trace")
    status: str = Field("completed", description="Analysis status: 'completed' or 'failed'")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal issues encountered during analysis")
