"""Pydantic schemas for code intelligence analysis requests and responses."""

from typing import List
from pydantic import BaseModel, Field

from app.code_intelligence.models import (
    CodebaseSummary,
    CodeEntity,
    CodeFile,
    CodeStructureNode,
    DependencyRelation,
    FileParseError,
)
from app.schemas.repository import RepositoryInfo


class CodeAnalysisRequest(BaseModel):
    """Request payload for static code intelligence analysis."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository HTTPS URL (e.g. https://github.com/owner/repo)",
        examples=["https://github.com/octocat/Hello-World"],
    )


class CodeAnalysisResponse(BaseModel):
    """Response payload containing full code intelligence metadata."""

    repository: RepositoryInfo = Field(..., description="Repository metadata")
    summary: CodebaseSummary = Field(
        ..., description="Quantitative summary of code entities and languages"
    )
    files: List[CodeFile] = Field(
        default_factory=list, description="Detailed per-file analysis and entity listings"
    )
    entities: List[CodeEntity] = Field(
        default_factory=list, description="Flat list of all discovered code entities"
    )
    dependencies: List[DependencyRelation] = Field(
        default_factory=list, description="Discovered internal and external dependency relationships"
    )
    codebase_tree: List[CodeStructureNode] = Field(
        default_factory=list,
        description="Hierarchical codebase tree linking directories, files, classes, and functions",
    )
    errors: List[FileParseError] = Field(
        default_factory=list, description="Parsing errors encountered in individual files"
    )
    status: str = Field("success", description="Status indicator")
