"""Domain models and Pydantic schemas for static security analysis and risk detection."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class SecuritySeverity(str, Enum):
    """Severity levels representing the potential impact of a security finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class SecurityConfidence(str, Enum):
    """Confidence levels representing how strongly static evidence supports detection."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SecurityCategory(str, Enum):
    """Functional categories for security findings."""

    CREDENTIALS = "credentials"
    CODE_EXECUTION = "code_execution"
    COMMAND_INJECTION = "command_injection"
    SQL_INJECTION = "sql_injection"
    DESERIALIZATION = "deserialization"
    CRYPTOGRAPHY = "cryptography"
    INSECURE_COMMUNICATION = "insecure_communication"
    ERROR_HANDLING = "error_handling"


class SecurityFinding(BaseModel):
    """An individual static security finding or risk indicator."""

    finding_id: str = Field(..., description="Unique finding identifier")
    rule_id: str = Field(..., description="Identifier of the detection rule (e.g. 'PYTHON_HARDCODED_CREDENTIAL')")
    title: str = Field(..., description="Short descriptive title of the finding")
    description: str = Field(..., description="Detailed explanation of the detected pattern and potential risk")
    severity: SecuritySeverity = Field(..., description="Severity level representing impact")
    confidence: SecurityConfidence = Field(..., description="Confidence level based on static evidence")
    file_path: str = Field(..., description="Repository-relative file path")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    entity_name: Optional[str] = Field(None, description="Name of enclosing function/class if available")
    evidence_summary: str = Field(..., description="Safe summary of the static pattern WITHOUT exposing secrets")
    remediation: str = Field(..., description="Actionable remediation guidance")
    cwe_id: Optional[str] = Field(None, description="CWE identifier when accurately applicable (e.g. 'CWE-798')")
    category: SecurityCategory = Field(..., description="Security category")


class SecuritySummary(BaseModel):
    """Aggregated counts of findings by severity."""

    critical: int = Field(0, description="Count of critical-severity findings")
    high: int = Field(0, description="Count of high-severity findings")
    medium: int = Field(0, description="Count of medium-severity findings")
    low: int = Field(0, description="Count of low-severity findings")
    informational: int = Field(0, description="Count of informational findings")
    total: int = Field(0, description="Total count of security findings")


class AnalysisStats(BaseModel):
    """File processing and coverage metrics for security analysis."""

    files_discovered: int = Field(0, description="Total files discovered eligible for scanning")
    files_analyzed: int = Field(0, description="Total files successfully parsed and analyzed")
    files_skipped: int = Field(0, description="Total files skipped due to size, unsupported type, or parse errors")


class SecurityAnalysisRequest(BaseModel):
    """Request payload for repository security analysis."""

    repository_url: str = Field(..., description="Public GitHub repository URL (https://github.com/owner/repo)")
    explain_with_llm: bool = Field(False, description="Optionally enrich report with an LLM security posture summary")


class SecurityAnalysisResponse(BaseModel):
    """Response payload containing security findings and risk summary."""

    repository: RepositoryInfo = Field(..., description="Repository metadata")
    analysis: AnalysisStats = Field(..., description="Scan and coverage statistics")
    summary: SecuritySummary = Field(..., description="Finding counts grouped by severity")
    findings: List[SecurityFinding] = Field(default_factory=list, description="List of detected security findings")
    category_summary: Dict[str, int] = Field(default_factory=dict, description="Finding counts grouped by category")
    status: str = Field("completed", description="Analysis execution status")
    llm_summary: Optional[str] = Field(None, description="Optional LLM executive summary (if requested and configured)")
