"""Pydantic schemas and domain models for AI documentation generator."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class DocType(str, Enum):
    """Supported documentation types."""

    README = "readme"
    PROJECT_OVERVIEW = "project_overview"
    ARCHITECTURE = "architecture"
    MODULE = "module"
    API_REFERENCE = "api_reference"
    FUNCTION_REFERENCE = "function_reference"
    SETUP_GUIDE = "setup_guide"


class DocAudience(str, Enum):
    """Target audience for the generated documentation."""

    DEVELOPER = "developer"
    BEGINNER = "beginner"
    MAINTAINER = "maintainer"


class DocDetailLevel(str, Enum):
    """Detail level of generated documentation."""

    CONCISE = "concise"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


class DocSection(BaseModel):
    """A structured section within a generated document."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section Markdown content")
    subsections: List["DocSection"] = Field(
        default_factory=list,
        description="Optional nested subsections",
    )


class DocMetadata(BaseModel):
    """Metadata regarding documentation generation."""

    doc_type: str = Field(..., description="Documentation type generated")
    audience: str = Field("developer", description="Target audience")
    detail_level: str = Field("standard", description="Detail level")
    model: str = Field("gpt-4o-mini", description="LLM model or generator used")
    generation_time_seconds: float = Field(0.0, description="Generation duration in seconds")
    source_files_count: int = Field(0, description="Number of repository files analyzed")
    created_at: str = Field(..., description="ISO 8601 generation timestamp")


class DocGenerateRequest(BaseModel):
    """Request payload for generating repository documentation."""

    repository_url: str = Field(..., description="Public GitHub repository URL")
    doc_type: DocType = Field(DocType.README, description="Type of documentation to generate")
    target_path: Optional[str] = Field(
        None,
        description="Optional specific file or directory path within repository",
        max_length=500,
    )
    target_symbol: Optional[str] = Field(
        None,
        description="Optional function, class, or method name to document",
        max_length=200,
    )
    audience: DocAudience = Field(
        DocAudience.DEVELOPER,
        description="Target audience for tone and depth",
    )
    detail_level: DocDetailLevel = Field(
        DocDetailLevel.STANDARD,
        description="Desired level of detail",
    )
    user_instructions: Optional[str] = Field(
        None,
        description="Optional custom developer guidance or focus points",
        max_length=3000,
    )


class DocGenerateResponse(BaseModel):
    """Complete response payload containing generated technical documentation."""

    document_id: str = Field(..., description="Unique document session identifier")
    repository: RepositoryInfo = Field(..., description="Repository metadata")
    doc_type: DocType = Field(..., description="Documentation type")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Full generated Markdown content")
    summary: str = Field(..., description="Brief executive summary of the document")
    sections: List[DocSection] = Field(default_factory=list, description="Parsed structured sections")
    source_files_used: List[str] = Field(
        default_factory=list,
        description="Repository-relative file paths analyzed to produce the document",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Information that could not be verified from the codebase",
    )
    unverified_items: List[str] = Field(
        default_factory=list,
        description="Items requiring manual developer confirmation",
    )
    metadata: DocMetadata = Field(..., description="Generation execution metadata")
    status: str = Field("completed", description="Generation status: 'completed' or 'failed'")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or notices")
