"""Domain models and Pydantic schemas for code quality analysis and repository health."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.code_intelligence.models import FileParseError
from app.schemas.repository import RepositoryInfo


class FindingSeverity(str, Enum):
    """Severity levels for code quality findings."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class FindingCategory(str, Enum):
    """Categories of code quality issues."""

    COMPLEXITY = "complexity"
    SIZE = "size"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    ERROR_HANDLING = "error_handling"
    STYLE = "style"
    DUPLICATION = "duplication"


class QualityFinding(BaseModel):
    """An individual static code quality finding or code smell."""

    id: str = Field(..., description="Unique finding identifier")
    rule_id: str = Field(..., description="Identifier of the triggered rule (e.g. 'FUNCTION_TOO_LONG')")
    rule_name: str = Field(..., description="Human-readable rule name")
    category: FindingCategory = Field(..., description="Classification category")
    severity: FindingSeverity = Field(..., description="Severity level")
    file_path: str = Field(..., description="Relative file path from repository root")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    entity_name: Optional[str] = Field(None, description="Name of affected function/class if applicable")
    entity_type: Optional[str] = Field(None, description="Entity type: function, method, class, module")
    message: str = Field(..., description="Detailed description of the issue")
    suggestion: str = Field(..., description="Actionable recommendation to resolve the finding")
    metric_value: Optional[float] = Field(None, description="Observed metric value (e.g. 65 lines, 18 complexity)")
    threshold: Optional[float] = Field(None, description="Configured rule threshold")


class EntityQualityMetrics(BaseModel):
    """Quality metrics computed for an individual function, method, or class."""

    entity_name: str = Field(..., description="Entity name")
    entity_type: str = Field(..., description="Entity type")
    file_path: str = Field(..., description="Relative file path")
    start_line: int = Field(..., description="Start line")
    end_line: int = Field(..., description="End line")
    lines_count: int = Field(..., description="Total lines in entity definition")
    cyclomatic_complexity: int = Field(1, description="Cyclomatic complexity score")
    max_nesting_depth: int = Field(0, description="Maximum control flow nesting depth")
    parameter_count: int = Field(0, description="Number of parameters")
    has_docstring: bool = Field(False, description="Whether docstring or JSDoc exists")


class FileQualitySummary(BaseModel):
    """Aggregated quality metrics and health score for a single file."""

    file_path: str = Field(..., description="Relative file path")
    language: str = Field(..., description="Programming language")
    total_lines: int = Field(..., description="Total line count")
    code_lines: int = Field(..., description="Lines containing executable code")
    comment_lines: int = Field(..., description="Comment lines")
    blank_lines: int = Field(..., description="Blank lines")
    functions_count: int = Field(0, description="Functions and methods in this file")
    classes_count: int = Field(0, description="Classes in this file")
    average_complexity: float = Field(1.0, description="Average cyclomatic complexity of functions")
    max_complexity: int = Field(1, description="Highest cyclomatic complexity in file")
    findings_count: int = Field(0, description="Total findings detected in this file")
    health_score: float = Field(100.0, description="File maintainability / quality score (0-100)")
    letter_grade: str = Field("A", description="Letter grade for file quality: A, B, C, D, F")


class RepositoryQualityMetrics(BaseModel):
    """Aggregate quality and complexity metrics across the whole repository."""

    total_lines: int = Field(..., description="Cumulative total lines across analyzed files")
    code_lines: int = Field(..., description="Cumulative lines of code")
    comment_lines: int = Field(..., description="Cumulative comment lines")
    blank_lines: int = Field(..., description="Cumulative blank lines")
    total_files_analyzed: int = Field(..., description="Number of successfully analyzed code files")
    files_with_issues: int = Field(..., description="Number of files with at least one finding")
    total_functions: int = Field(..., description="Total functions and methods analyzed")
    total_classes: int = Field(..., description="Total classes analyzed")
    average_function_length: float = Field(..., description="Mean lines of code per function/method")
    average_cyclomatic_complexity: float = Field(..., description="Mean cyclomatic complexity score")
    max_cyclomatic_complexity: int = Field(..., description="Maximum cyclomatic complexity observed")
    docstring_coverage_percentage: float = Field(
        ..., description="Percentage of public functions/classes with documentation (0-100)"
    )
    duplicate_blocks_count: int = Field(0, description="Number of duplicate code blocks detected")


class HealthScoreBreakdown(BaseModel):
    """Sub-scores and overall health letter grade."""

    maintainability_score: float = Field(..., description="Maintainability sub-score (0-100)")
    complexity_score: float = Field(..., description="Complexity sub-score (0-100)")
    documentation_score: float = Field(..., description="Documentation coverage sub-score (0-100)")
    reliability_score: float = Field(..., description="Error handling and code smell sub-score (0-100)")
    overall_score: float = Field(..., description="Composite repository health score (0-100)")
    letter_grade: str = Field(..., description="Letter grade: 'A', 'B', 'C', 'D', 'F'")


class CodeQualityRequest(BaseModel):
    """Request payload to analyze repository code quality."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository HTTPS URL",
        examples=["https://github.com/octocat/Hello-World"],
    )


class CodeQualityResponse(BaseModel):
    """Response payload containing comprehensive code quality analysis and repository health."""

    repository: RepositoryInfo = Field(..., description="Repository metadata")
    health: HealthScoreBreakdown = Field(..., description="Health scores and overall grade")
    metrics: RepositoryQualityMetrics = Field(..., description="Aggregated repository metrics")
    findings: List[QualityFinding] = Field(default_factory=list, description="All detected code quality findings")
    file_summaries: List[FileQualitySummary] = Field(default_factory=list, description="Per-file quality summaries")
    category_breakdown: Dict[str, int] = Field(default_factory=dict, description="Finding counts grouped by category")
    severity_breakdown: Dict[str, int] = Field(default_factory=dict, description="Finding counts grouped by severity")
    parsing_errors: List[FileParseError] = Field(default_factory=list, description="Files that encountered parse errors")
    status: str = Field("success", description="Status indicator")
