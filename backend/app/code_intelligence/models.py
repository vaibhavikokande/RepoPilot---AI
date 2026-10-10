"""Domain models for code intelligence, AST analysis, and codebase structure."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CodeEntity(BaseModel):
    """A structured code entity (class, function, method, interface, etc.)."""

    name: str = Field(..., description="Entity identifier name")
    type: str = Field(
        ...,
        description="Type of entity: 'class', 'function', 'method', 'interface', 'type_alias', 'variable'",
    )
    file_path: str = Field(..., description="Relative file path from repository root")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    signature: Optional[str] = Field(
        None, description="Human-readable signature (e.g. 'def func(a: int) -> str')"
    )
    docstring: Optional[str] = Field(None, description="Docstring or JSDoc if present")
    parent: Optional[str] = Field(
        None, description="Parent entity name (e.g. enclosing class name for methods)"
    )
    decorators: List[str] = Field(
        default_factory=list, description="Decorators applied to the entity"
    )
    parameters: List[str] = Field(
        default_factory=list, description="List of parameter names or declarations"
    )
    return_type: Optional[str] = Field(
        None, description="Return type annotation if declared"
    )
    visibility: Optional[str] = Field(
        None, description="Visibility: 'public', 'private', or 'protected'"
    )


class CodeImport(BaseModel):
    """An import statement within a source file."""

    module: str = Field(..., description="Imported module or package path")
    imported_names: List[str] = Field(
        default_factory=list,
        description="Specific imported symbols/names (e.g. ['User', 'get_db'])",
    )
    alias: Optional[str] = Field(None, description="Import alias if specified (e.g. 'np')")
    is_relative: bool = Field(
        False, description="Whether this is a relative import (e.g. from .service import ...)"
    )
    line_number: int = Field(1, description="1-indexed line where import occurs")
    source_file: str = Field(..., description="File where this import statement exists")


class CodeFile(BaseModel):
    """Metadata and extracted entities for a parsed source file."""

    path: str = Field(..., description="Relative file path from repository root")
    language: str = Field(..., description="Detected programming language")
    size_bytes: int = Field(..., description="File size in bytes")
    lines: int = Field(..., description="Total line count")
    entities: List[CodeEntity] = Field(
        default_factory=list, description="Extracted code entities in this file"
    )
    imports: List[CodeImport] = Field(
        default_factory=list, description="Import statements found in this file"
    )


class FileParseError(BaseModel):
    """Details of a file that failed static parsing."""

    path: str = Field(..., description="Relative path of the failed file")
    language: str = Field(..., description="Attempted language")
    error_type: str = Field(..., description="Category of error (e.g. 'SyntaxError')")
    message: str = Field(..., description="Sanitized error description")


class DependencyRelation(BaseModel):
    """Dependency relationship between files or modules."""

    source_file: str = Field(..., description="File containing the import statement")
    target_module: str = Field(..., description="Import target specification")
    imported_symbols: List[str] = Field(
        default_factory=list, description="Symbols imported from the target"
    )
    resolved_target_file: Optional[str] = Field(
        None, description="Relative path to local repository file if internal"
    )
    is_internal: bool = Field(
        False, description="True if target resolves to a file within this repository"
    )


class CodebaseSummary(BaseModel):
    """Quantitative summary of code entities across the entire repository."""

    files_analyzed: int = Field(..., description="Count of successfully parsed files")
    languages: Dict[str, int] = Field(
        default_factory=dict, description="Distribution of analyzed files by language"
    )
    classes: int = Field(0, description="Total class definitions found")
    functions: int = Field(0, description="Total top-level functions found")
    methods: int = Field(0, description="Total class methods found")
    imports: int = Field(0, description="Total import statements found")
    interfaces: int = Field(0, description="Total interface definitions found (TS)")
    types: int = Field(0, description="Total type alias definitions found (TS)")
    files_with_errors: int = Field(0, description="Count of files that failed to parse")


class CodeStructureNode(BaseModel):
    """Hierarchical node for building the codebase structural map."""

    name: str = Field(..., description="Node label (directory name, file name, entity name)")
    type: str = Field(
        ...,
        description="Node type: 'directory', 'file', 'class', 'function', 'interface', 'method'",
    )
    path: str = Field(..., description="Repository path or entity path")
    line_info: Optional[str] = Field(None, description="Line range if applicable (e.g. 'L10-L45')")
    docstring: Optional[str] = Field(None, description="Brief docstring excerpt if applicable")
    children: Optional[List["CodeStructureNode"]] = Field(
        None, description="Child nodes in the hierarchy"
    )


class CodeChunk(BaseModel):
    """A granular, semantically bounded code chunk ready for search and RAG indexing."""

    chunk_id: str = Field(..., description="Unique chunk identifier (e.g. file_path#entity#L1-L20)")
    file_path: str = Field(..., description="Relative file path from repository root")
    entity_name: str = Field(..., description="Name of the enclosed code entity or module")
    entity_type: str = Field(
        ...,
        description="Entity type: 'class', 'function', 'method', 'interface', 'type_alias', 'file_module'",
    )
    language: str = Field(..., description="Programming language")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    signature: Optional[str] = Field(None, description="Function/class signature")
    docstring: Optional[str] = Field(None, description="Docstring or comment if present")
    parent: Optional[str] = Field(None, description="Enclosing class or module name")
    parameters: List[str] = Field(default_factory=list, description="Parameter list")
    return_type: Optional[str] = Field(None, description="Return type annotation")
    decorators: List[str] = Field(default_factory=list, description="Decorators applied")
    visibility: Optional[str] = Field(None, description="Visibility: public, private, protected")
    code_content: str = Field(..., description="Source code text of this chunk")
    context_header: str = Field(
        ..., description="Descriptive context line (File, Enclosing scope, Signature)"
    )
    tokens_estimate: int = Field(0, description="Heuristic estimate of token count")

