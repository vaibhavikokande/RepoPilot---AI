"""Domain models and exceptions for AI documentation generator."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.documentation import (
    DocAudience,
    DocDetailLevel,
    DocGenerateRequest,
    DocGenerateResponse,
    DocMetadata,
    DocSection,
    DocType,
)


class DocGeneratorError(Exception):
    """Base exception for documentation generator errors."""
    pass


class DocValidationError(DocGeneratorError):
    """Raised when documentation request fails validation."""
    pass


class DocTargetNotFoundError(DocGeneratorError):
    """Raised when target file or symbol is not found in the repository."""
    pass


class DocExecutionError(DocGeneratorError):
    """Raised when an internal error occurs during documentation generation."""
    pass


class DiscoveredRoute(BaseModel):
    """An API route discovered from codebase source files."""

    method: str = Field(..., description="HTTP Method (GET, POST, PUT, DELETE, etc.)")
    path: str = Field(..., description="Route URL path (e.g. /api/v1/health)")
    handler_name: str = Field(..., description="Handler function name")
    file_path: str = Field(..., description="Repository-relative file path where defined")
    line_number: int = Field(..., description="Line number of route definition")
    docstring: Optional[str] = Field(None, description="Handler docstring or summary")


class DiscoveredSymbol(BaseModel):
    """A function, method, or class discovered from code intelligence."""

    name: str = Field(..., description="Symbol name")
    symbol_type: str = Field(..., description="Type: function, class, method, interface")
    file_path: str = Field(..., description="Repository-relative file path")
    start_line: int = Field(..., description="Start line")
    end_line: int = Field(..., description="End line")
    signature: Optional[str] = Field(None, description="Function/class signature")
    docstring: Optional[str] = Field(None, description="Existing docstring")


class CollectedDocContext(BaseModel):
    """Structured context gathered from repository for documentation generation."""

    doc_type: DocType
    manifest_files: Dict[str, str] = Field(default_factory=dict, description="Filename -> content of manifests")
    existing_docs: Dict[str, str] = Field(default_factory=dict, description="Filename -> content of existing docs")
    file_tree_summary: str = Field("", description="Condensed text outline of directory tree")
    discovered_routes: List[DiscoveredRoute] = Field(default_factory=list, description="Extracted API routes")
    discovered_symbols: List[DiscoveredSymbol] = Field(default_factory=list, description="Extracted code symbols")
    environment_vars: List[str] = Field(default_factory=list, description="Environment variable names referenced in code")
    test_frameworks: List[str] = Field(default_factory=list, description="Detected testing tools/frameworks")
    target_content: Optional[str] = Field(None, description="Target file or symbol content if scoped")
    source_files_used: List[str] = Field(default_factory=list, description="All file paths included in context")
    missing_elements: List[str] = Field(default_factory=list, description="Noted missing files or elements")
