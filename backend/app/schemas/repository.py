"""Pydantic schemas for repository ingestion and analysis."""

from typing import Optional
from pydantic import BaseModel, Field


class RepositoryAnalyzeRequest(BaseModel):
    """Request payload for repository analysis."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository HTTPS URL (e.g. https://github.com/owner/repo)",
        examples=["https://github.com/octocat/Hello-World"],
    )


class RepositoryInfo(BaseModel):
    """Metadata about a GitHub repository."""

    name: str = Field(..., description="Repository name")
    owner: str = Field(..., description="Repository owner / organization")
    url: str = Field(..., description="Clean HTTPS URL to the repository")
    default_branch: Optional[str] = Field(
        None, description="Default branch name (e.g. main, master)"
    )


class FileInfo(BaseModel):
    """Information about a specific file."""

    path: str = Field(..., description="Relative path from repository root")
    size_bytes: int = Field(..., description="File size in bytes")


class RepositoryStatistics(BaseModel):
    """Statistical summary of repository contents."""

    total_files: int = Field(..., description="Total number of scanned files")
    total_directories: int = Field(
        ..., description="Total number of scanned directories"
    )
    total_size_bytes: int = Field(
        ..., description="Total size in bytes of all scanned files"
    )
    file_extensions: dict[str, int] = Field(
        default_factory=dict,
        description="Count of files grouped by extension",
    )
    largest_files: list[FileInfo] = Field(
        default_factory=list,
        description="Top largest files in the repository",
    )


class FileTreeNode(BaseModel):
    """Hierarchical node in a repository file tree."""

    name: str = Field(..., description="File or directory name")
    type: str = Field(..., description="'file' or 'directory'")
    path: str = Field(..., description="Relative path from repository root")
    size_bytes: Optional[int] = Field(
        None, description="Size in bytes (present for files)"
    )
    children: Optional[list["FileTreeNode"]] = Field(
        None, description="Child nodes (present for directories)"
    )


class RepositoryAnalyzeResponse(BaseModel):
    """Response payload for repository analysis."""

    repository: RepositoryInfo
    statistics: RepositoryStatistics
    languages: dict[str, int] = Field(
        default_factory=dict,
        description="Detected programming languages with file counts",
    )
    file_tree: list[FileTreeNode] = Field(
        default_factory=list,
        description="Hierarchical file tree representation",
    )
    status: str = Field("success", description="Status indicator")
