"""Domain models and Pydantic schemas for AI-powered unit test generation."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryInfo


class TestTarget(BaseModel):
    """Metadata describing the target function or method to test."""

    __test__ = False

    file_path: str = Field(..., description="Repository-relative path of the target source file")
    entity_name: str = Field(..., description="Name of the target function or method")
    entity_type: str = Field("function", description="Type of entity: 'function' or 'method'")
    parent_class: Optional[str] = Field(None, description="Enclosing class name if target is a method")
    start_line: int = Field(..., description="1-indexed starting line number")
    end_line: int = Field(..., description="1-indexed ending line number")
    signature: Optional[str] = Field(None, description="Function or method signature")
    docstring: Optional[str] = Field(None, description="Docstring if available")


class TestCaseDescription(BaseModel):
    """Summary of an individual test case generated for the target entity."""

    __test__ = False

    name: str = Field(..., description="Descriptive pytest function name (e.g. 'test_valid_email')")
    purpose: str = Field(..., description="Brief explanation of what condition this test verifies")


class ValidationResult(BaseModel):
    """Structural and syntax validation results of the generated test code."""

    syntax_valid: bool = Field(..., description="Whether generated code parses as valid Python AST")
    structure_valid: bool = Field(..., description="Whether expected pytest test functions were discovered")
    test_functions_found: int = Field(0, description="Count of test functions starting with 'test_'")
    syntax_error: Optional[str] = Field(None, description="Syntax error message if parsing failed")
    warnings: List[str] = Field(default_factory=list, description="Structural or safety warnings")
    execution_status: str = Field("not_run", description="Execution status ('not_run', 'passed', 'failed')")


class TestGenerationRequest(BaseModel):
    """Request payload for unit test generation."""

    __test__ = False

    repository_url: str = Field(..., description="Public GitHub repository URL (https://github.com/owner/repo)")
    file_path: str = Field(..., description="Repository-relative file path (e.g. 'app/services/user_service.py')")
    entity_name: str = Field(..., description="Name of the function or method to generate tests for")
    start_line: Optional[int] = Field(None, description="Optional starting line to disambiguate overloaded names")
    end_line: Optional[int] = Field(None, description="Optional ending line")


class TestGenerationResponse(BaseModel):
    """Response payload containing generated unit tests and explanations."""

    __test__ = False

    repository: RepositoryInfo = Field(..., description="Repository metadata")
    target: TestTarget = Field(..., description="Details of the tested function or method")
    framework: str = Field("pytest", description="Testing framework used for generation")
    test_cases: List[TestCaseDescription] = Field(default_factory=list, description="Descriptions of generated test cases")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made regarding behavior or contracts")
    test_code: str = Field(..., description="Complete executable pytest source code")
    validation: ValidationResult = Field(..., description="Syntax and structural validation output")
    file_name: str = Field(..., description="Suggested filename for saving tests (e.g. 'test_validate_email.py')")
    status: str = Field("completed", description="Generation status ('completed', 'failed')")
