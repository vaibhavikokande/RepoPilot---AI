"""Pydantic schemas for intelligent code search requests and responses."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class CodeSearchRequest(BaseModel):
    """Request payload for lexical and metadata-based code search."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository HTTPS URL (e.g. https://github.com/owner/repo)",
        examples=["https://github.com/octocat/Hello-World"],
    )
    query: str = Field(
        ...,
        description="Search query (e.g. 'Where is user authentication handled?', 'UserService', 'jwt token')",
        min_length=1,
        examples=["Where is user authentication handled?"],
    )
    limit: int = Field(
        10,
        description="Maximum number of ranked results to return",
        ge=1,
        le=50,
    )
    entity_types: Optional[List[str]] = Field(
        None,
        description="Optional list of entity types to filter by (e.g. ['function', 'class', 'method'])",
    )


class CodeSearchResultItem(BaseModel):
    """An individual search hit representing a matched code chunk."""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    file_path: str = Field(..., description="Relative file path from repository root")
    entity_name: str = Field(..., description="Name of the matched code entity or module")
    entity_type: str = Field(..., description="Entity type: class, function, method, interface, file_module")
    language: str = Field(..., description="Programming language")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    signature: Optional[str] = Field(None, description="Signature if applicable")
    docstring: Optional[str] = Field(None, description="Docstring excerpt if present")
    parent: Optional[str] = Field(None, description="Enclosing class or scope")
    parameters: List[str] = Field(default_factory=list, description="Parameter list")
    return_type: Optional[str] = Field(None, description="Return type annotation")
    code_snippet: str = Field(..., description="Actual code snippet content of the chunk")
    context_header: str = Field(..., description="Contextual summary header")
    tokens_estimate: int = Field(0, description="Heuristic token count")
    score: float = Field(..., description="Lexical and metadata relevance score")
    match_reasons: List[str] = Field(default_factory=list, description="Specific matching criteria met")
    explanation: str = Field(..., description="Concise human-readable explanation of why this chunk matched")


class CodeSearchResponse(BaseModel):
    """Response payload containing ranked code search results."""

    repository: RepositoryInfo = Field(..., description="Repository metadata")
    query: str = Field(..., description="Original search query")
    total_chunks_indexed: int = Field(..., description="Total semantic code chunks indexed")
    total_results: int = Field(..., description="Number of results matching query")
    results: List[CodeSearchResultItem] = Field(default_factory=list, description="Ranked matching code chunks")
    status: str = Field("success", description="Status indicator")
