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


class RepositoryIndexRequest(BaseModel):
    """Request payload to index repository chunks into vector store."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository HTTPS URL",
        examples=["https://github.com/octocat/Hello-World"],
    )
    force_reindex: bool = Field(
        False,
        description="If True, clears existing vector index and re-computes embeddings from scratch",
    )


class RepositoryIndexResponse(BaseModel):
    """Response payload returned after indexing code chunks."""

    repository: RepositoryInfo = Field(..., description="Repository metadata")
    status: str = Field("success", description="Indexing status")
    files_processed: int = Field(..., description="Number of source files parsed")
    chunks_indexed: int = Field(..., description="Number of semantic chunks embedded and stored")
    chunks_skipped: int = Field(0, description="Chunks skipped (e.g. empty or non-parseable)")
    embedding_model: str = Field(..., description="Name of embedding model used")
    dimension: int = Field(..., description="Embedding vector dimension")
    total_vectors_in_index: int = Field(..., description="Total vectors currently persisted in collection")
    message: str = Field("Repository successfully indexed", description="Status message")


class SemanticSearchRequest(BaseModel):
    """Request payload for semantic and hybrid vector retrieval."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository HTTPS URL",
        examples=["https://github.com/octocat/Hello-World"],
    )
    query: str = Field(
        ...,
        description="Natural language query or code search phrase",
        min_length=1,
        examples=["Where does the application validate user login credentials?"],
    )
    limit: int = Field(
        10,
        description="Maximum result count",
        ge=1,
        le=50,
    )
    entity_types: Optional[List[str]] = Field(
        None,
        description="Optional filter by entity types (e.g. ['function', 'class', 'method'])",
    )
    mode: str = Field(
        "semantic",
        description="Search mode: 'semantic' (pure vector), 'lexical' (keyword), or 'hybrid' (RRF fusion)",
    )


class SemanticSearchResultItem(BaseModel):
    """An individual hit returned from semantic or hybrid retrieval."""

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
    code_snippet: str = Field(..., description="Actual code snippet content of the chunk")
    context_header: str = Field(..., description="Contextual summary header")
    tokens_estimate: int = Field(0, description="Heuristic token count")
    score: float = Field(..., description="Similarity score (semantic) or RRF score (hybrid)")
    search_mode: str = Field(..., description="Search mode that produced this result ('semantic', 'hybrid', 'lexical')")
    match_reasons: List[str] = Field(default_factory=list, description="Criteria met during retrieval")
    explanation: str = Field(..., description="Concise human-readable explanation")


class SemanticSearchResponse(BaseModel):
    """Response payload containing ranked semantic or hybrid results."""

    repository: RepositoryInfo = Field(..., description="Repository metadata")
    query: str = Field(..., description="Original search query")
    search_mode: str = Field(..., description="Applied search mode")
    total_results: int = Field(..., description="Count of returned results")
    results: List[SemanticSearchResultItem] = Field(default_factory=list, description="Ranked matching code chunks")
    status: str = Field("success", description="Status indicator")

