"""Pydantic schemas and data models for RAG-based code understanding."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class CodeCitation(BaseModel):
    """A verified source citation referencing a code chunk in the generated answer."""

    source_id: str = Field(
        ...,
        description="Source identifier matching citation tag in the answer (e.g. 'S1', 'S2')",
        examples=["S1"],
    )
    file_path: str = Field(
        ...,
        description="Relative file path from the repository root",
        examples=["app/core/auth.py"],
    )
    start_line: int = Field(
        ...,
        description="1-indexed starting line number of the cited code chunk",
        examples=[15],
    )
    end_line: int = Field(
        ...,
        description="1-indexed ending line number of the cited code chunk",
        examples=[42],
    )
    entity_name: str = Field(
        ...,
        description="Name of the cited code entity (e.g. function or class name) or module",
        examples=["authenticate_user"],
    )
    entity_type: str = Field(
        ...,
        description="Type of entity: function, class, method, interface, file_module",
        examples=["function"],
    )
    score: float = Field(
        ...,
        description="Retrieval relevance or similarity score",
        examples=[0.88],
    )


class RetrievedSource(BaseModel):
    """A code chunk retrieved from the repository and provided as context for answer synthesis."""

    source_id: str = Field(
        ...,
        description="Deterministic identifier assigned to this source chunk (e.g. 'S1')",
        examples=["S1"],
    )
    chunk_id: str = Field(
        ...,
        description="Underlying unique chunk identifier from vector/AST index",
    )
    file_path: str = Field(
        ...,
        description="Relative file path from the repository root",
    )
    start_line: int = Field(
        ...,
        description="1-indexed starting line number",
    )
    end_line: int = Field(
        ...,
        description="1-indexed ending line number",
    )
    entity_name: str = Field(
        ...,
        description="Name of the code entity or module",
    )
    entity_type: str = Field(
        ...,
        description="Type of entity: function, class, method, interface, file_module",
    )
    language: str = Field(
        ...,
        description="Programming language of the source file",
    )
    signature: Optional[str] = Field(
        None,
        description="Function or class signature if available",
    )
    docstring: Optional[str] = Field(
        None,
        description="Docstring or comment excerpt if available",
    )
    code_content: str = Field(
        ...,
        description="Source code content of this chunk",
    )
    score: float = Field(
        ...,
        description="Retrieval relevance score",
    )


class RAGRequest(BaseModel):
    """Request payload for asking natural language questions about a repository."""

    repository_url: str = Field(
        ...,
        description="Public GitHub repository HTTPS URL",
        examples=["https://github.com/octocat/Hello-World"],
    )
    question: str = Field(
        ...,
        description="Natural language question about the repository",
        min_length=1,
        examples=["How does user authentication work in this project?"],
    )
    top_k: int = Field(
        5,
        description="Maximum number of relevant code chunks to retrieve and ground against",
        ge=1,
        le=20,
    )


class RAGResponse(BaseModel):
    """Response payload containing grounded answer and verified code citations."""

    repository: RepositoryInfo = Field(
        ...,
        description="Repository metadata",
    )
    question: str = Field(
        ...,
        description="Original question asked by the user",
    )
    answer: str = Field(
        ...,
        description="LLM-generated answer strictly grounded in retrieved code evidence",
    )
    citations: List[CodeCitation] = Field(
        default_factory=list,
        description="Verified source citations explicitly referenced in the answer",
    )
    sources: List[RetrievedSource] = Field(
        default_factory=list,
        description="Retrieved code sources provided as context for answer generation",
    )
    retrieved_chunks: int = Field(
        ...,
        description="Total number of code chunks retrieved for this question",
    )
    status: str = Field(
        "success",
        description="Status indicator",
    )
