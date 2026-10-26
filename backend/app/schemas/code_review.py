"""Domain models and Pydantic schemas for AI-powered code review."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class CodeReviewFinding(BaseModel):
    """An individual actionable finding from code review."""

    finding_id: str = Field(..., description="Unique finding identifier (e.g. 'cr_abc123')")
    title: str = Field(..., description="Short, descriptive title of the finding")
    category: str = Field(
        ...,
        description="Category: 'correctness', 'security', 'performance', 'maintainability', 'readability', 'testing'",
    )
    severity: str = Field(
        ...,
        description="Severity: 'critical', 'high', 'medium', 'low', 'info'",
    )
    confidence: str = Field(
        "high",
        description="Confidence level: 'high', 'medium', 'low'",
    )
    file_path: str = Field(..., description="Repository-relative path of the source file")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    entity_name: Optional[str] = Field(None, description="Function, method, or class name if applicable")
    problem: str = Field(..., description="Clear explanation of the identified issue or risk")
    evidence: str = Field(..., description="Exact code snippet or statement from the source file")
    recommendation: str = Field(..., description="Actionable guidance on how to resolve the issue")
    suggested_change: Optional[str] = Field(
        None,
        description="Optional read-only suggested replacement code snippet or diff",
    )
    source: str = Field(
        "ai_review",
        description="Origin of the finding: 'static_analysis' (deterministic) or 'ai_review' (LLM)",
    )
    is_verified: bool = Field(
        True,
        description="Whether line numbers and evidence were verified against source code",
    )


class ReviewSummary(BaseModel):
    """High-level summary of code review findings."""

    total_findings: int = Field(0, description="Total number of findings identified")
    by_severity: Dict[str, int] = Field(
        default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        description="Finding counts grouped by severity",
    )
    by_category: Dict[str, int] = Field(
        default_factory=lambda: {
            "correctness": 0,
            "security": 0,
            "performance": 0,
            "maintainability": 0,
            "readability": 0,
            "testing": 0,
        },
        description="Finding counts grouped by category",
    )
    executive_summary: str = Field(
        ...,
        description="Brief narrative summary of code quality and key recommendations",
    )
    deterministic_count: int = Field(0, description="Count of deterministic static analysis findings")
    ai_count: int = Field(0, description="Count of AI-synthesized findings")


class ReviewMetadata(BaseModel):
    """Execution metadata and configuration for the review run."""

    ai_available: bool = Field(True, description="Whether LLM analysis was available and used")
    model_used: str = Field("gpt-4o-mini", description="LLM model identifier or 'deterministic_engine'")
    review_focus: str = Field("all", description="Focus requested: 'all', 'bugs', 'security', 'performance', etc.")
    lines_reviewed: int = Field(0, description="Number of source lines analyzed")
    deterministic_rules_applied: int = Field(0, description="Number of static rules evaluated")


class CodeReviewRequest(BaseModel):
    """Request payload to initiate a code review."""

    repository_url: str = Field(..., description="Public GitHub repository URL (https://github.com/owner/repo)")
    file_path: str = Field(..., description="Repository-relative file path (e.g. 'app/services/calculator.py')")
    entity_name: Optional[str] = Field(None, description="Optional target function or class name")
    review_focus: str = Field(
        "all",
        description="Review focus: 'all', 'correctness', 'security', 'performance', 'maintainability'",
    )
    user_instructions: Optional[str] = Field(
        None,
        description="Optional custom developer questions or instructions for the reviewer",
    )


class CodeReviewResponse(BaseModel):
    """Structured response containing code review findings and suggestions."""

    review_id: str = Field(..., description="Unique review run identifier (UUID)")
    repository: RepositoryInfo = Field(..., description="Repository metadata")
    file_path: str = Field(..., description="Path of the reviewed source file")
    entity_name: Optional[str] = Field(None, description="Target entity if specified")
    summary: ReviewSummary = Field(..., description="Aggregated findings summary")
    findings: List[CodeReviewFinding] = Field(default_factory=list, description="List of actionable findings")
    metadata: ReviewMetadata = Field(..., description="Execution metadata")
    warnings: List[str] = Field(default_factory=list, description="Any execution notices or limitations")
    status: str = Field("completed", description="Review status: 'completed' or 'failed'")
