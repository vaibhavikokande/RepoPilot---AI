"""Unit and integration tests for Day 9 AI-Powered Unit Test Generation."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rag.generator import BaseLLMGenerator
from app.schemas.repository import RepositoryInfo
from app.schemas.test_generation import (
    TestGenerationRequest,
    TestGenerationResponse,
)
from app.test_generation import (
    ContextBuilder,
    ContextBuilderError,
    EntityNotFoundError,
    PromptBuilder,
    TestValidator,
    UnitTestGenerator,
    UnsupportedLanguageError,
)
from app.services.repository_service import (
    RepositoryAccessError,
    RepositoryCloningError,
)

client = TestClient(app)


class TestContextBuilder:
    """Tests for locating entities and building source context."""

    @pytest.fixture
    def sample_repo(self, tmp_path):
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Create sample service file
        service_file = repo_dir / "user_service.py"
        service_file.write_text(
            'import re\n'
            'from typing import Optional\n'
            '\n'
            'def validate_email(email: str, allow_empty: bool = False) -> bool:\n'
            '    """Validate email address format.\n'
            '    \n'
            '    Args:\n'
            '        email: Email string to check.\n'
            '        allow_empty: Whether empty string is allowed.\n'
            '    """\n'
            '    if not email:\n'
            '        return allow_empty\n'
            '    pattern = r"^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$"\n'
            '    return bool(re.match(pattern, email))\n'
            '\n'
            'class UserManager:\n'
            '    """User domain manager."""\n'
            '    def __init__(self, db_session=None):\n'
            '        self.db = db_session\n'
            '    \n'
            '    def authenticate(self, username: str, token: str) -> bool:\n'
            '        """Authenticate user token."""\n'
            '        if not username or not token:\n'
            '            return False\n'
            '        return len(token) >= 8\n',
            encoding="utf-8",
        )

        # Create non-python file
        js_file = repo_dir / "index.js"
        js_file.write_text("function test() {}", encoding="utf-8")

        return repo_dir

    def test_extract_module_level_function(self, sample_repo):
        builder = ContextBuilder()
        ctx = builder.build_context(
            repo_path=sample_repo,
            file_path="user_service.py",
            entity_name="validate_email",
        )

        assert ctx.target.entity_name == "validate_email"
        assert ctx.target.entity_type == "function"
        assert ctx.target.parent_class is None
        assert "def validate_email" in ctx.function_source
        assert "from user_service import validate_email" in ctx.import_statement
        assert any("import re" in imp for imp in ctx.module_imports)

    def test_extract_class_method(self, sample_repo):
        builder = ContextBuilder()
        ctx = builder.build_context(
            repo_path=sample_repo,
            file_path="user_service.py",
            entity_name="authenticate",
        )

        assert ctx.target.entity_name == "authenticate"
        assert ctx.target.entity_type == "method"
        assert ctx.target.parent_class == "UserManager"
        assert "def authenticate" in ctx.function_source
        assert ctx.class_context is not None
        assert "class UserManager" in ctx.class_context
        assert "from user_service import UserManager" in ctx.import_statement

    def test_entity_not_found_raises_error(self, sample_repo):
        builder = ContextBuilder()
        with pytest.raises(EntityNotFoundError, match="was not found"):
            builder.build_context(
                repo_path=sample_repo,
                file_path="user_service.py",
                entity_name="nonexistent_function",
            )

    def test_file_not_found_raises_error(self, sample_repo):
        builder = ContextBuilder()
        with pytest.raises(FileNotFoundError, match="does not exist"):
            builder.build_context(
                repo_path=sample_repo,
                file_path="missing_file.py",
                entity_name="some_function",
            )

    def test_unsupported_language_raises_error(self, sample_repo):
        builder = ContextBuilder()
        with pytest.raises(UnsupportedLanguageError, match="supports Python"):
            builder.build_context(
                repo_path=sample_repo,
                file_path="index.js",
                entity_name="test",
            )

    def test_path_traversal_rejected(self, sample_repo):
        builder = ContextBuilder()
        with pytest.raises(ContextBuilderError, match="traverses outside"):
            builder.build_context(
                repo_path=sample_repo,
                file_path="../../etc/passwd",
                entity_name="test",
            )


class TestTestValidator:
    """Tests for AST syntax checking and pytest structural verification."""

    def test_valid_pytest_code(self):
        code = (
            "import pytest\n"
            "from app.service import validate_email\n"
            "\n"
            "def test_valid_email():\n"
            "    assert validate_email('user@example.com') is True\n"
            "\n"
            "def test_invalid_email():\n"
            "    assert validate_email('invalid') is False\n"
        )
        validator = TestValidator()
        result = validator.validate(code)

        assert result.syntax_valid is True
        assert result.structure_valid is True
        assert result.test_functions_found == 2
        assert result.syntax_error is None

    def test_syntax_error_detected(self):
        code = (
            "import pytest\n"
            "def test_broken(\n"
            "    assert True\n"
        )
        validator = TestValidator()
        result = validator.validate(code)

        assert result.syntax_valid is False
        assert result.structure_valid is False
        assert result.test_functions_found == 0
        assert result.syntax_error is not None
        assert "SyntaxError" in result.syntax_error

    def test_empty_code_rejected(self):
        validator = TestValidator()
        result = validator.validate("")

        assert result.syntax_valid is False
        assert result.structure_valid is False
        assert "empty" in result.syntax_error.lower()

    def test_missing_test_functions_warning(self):
        code = (
            "import pytest\n"
            "def helper():\n"
            "    return 42\n"
        )
        validator = TestValidator()
        result = validator.validate(code)

        assert result.syntax_valid is True
        assert result.structure_valid is False
        assert result.test_functions_found == 0
        assert any("test_" in w for w in result.warnings)

    def test_test_class_methods_counted(self):
        code = (
            "import pytest\n"
            "class TestUserManager:\n"
            "    def test_login(self):\n"
            "        assert True\n"
            "    def test_logout(self):\n"
            "        assert True\n"
        )
        validator = TestValidator()
        result = validator.validate(code)

        assert result.syntax_valid is True
        assert result.structure_valid is True
        assert result.test_functions_found == 2


class TestUnitTestGenerator:
    """Tests for prompt building and test generation coordinator."""

    @pytest.mark.anyio
    async def test_generator_deterministic_fallback(self, tmp_path):
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()
        code_file = repo_dir / "math_utils.py"
        code_file.write_text(
            "def compute_tax(amount: float, rate: float = 0.1) -> float:\n"
            '    """Calculate tax for an amount."""\n'
            "    return amount * rate\n",
            encoding="utf-8",
        )

        repo_info = RepositoryInfo(
            name="mock_repo",
            owner="testowner",
            url="https://github.com/testowner/mock_repo",
            default_branch="main",
        )

        generator = UnitTestGenerator()
        response = await generator.generate_tests(
            repo_path=repo_dir,
            repo_info=repo_info,
            file_path="math_utils.py",
            entity_name="compute_tax",
        )

        assert response.status == "completed"
        assert response.target.entity_name == "compute_tax"
        assert response.framework == "pytest"
        assert len(response.test_cases) >= 2
        assert response.validation.syntax_valid is True
        assert response.validation.structure_valid is True
        assert "def test_" in response.test_code
        assert response.file_name == "test_compute_tax.py"

    @pytest.mark.anyio
    async def test_generator_with_mocked_llm_json_response(self, tmp_path):
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()
        code_file = repo_dir / "calc.py"
        code_file.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

        mock_llm = MagicMock(spec=BaseLLMGenerator)
        mock_llm.generate = AsyncMock(
            return_value=(
                '{\n'
                '  "framework": "pytest",\n'
                '  "test_cases": [\n'
                '    {"name": "test_add_positive_numbers", "purpose": "Checks standard integer addition"},\n'
                '    {"name": "test_add_negative_numbers", "purpose": "Checks negative integer addition"}\n'
                '  ],\n'
                '  "assumptions": ["Inputs are integers."],\n'
                '  "test_code": "import pytest\\nfrom calc import add\\n\\ndef test_add_positive_numbers():\\n    assert add(1, 2) == 3\\n\\ndef test_add_negative_numbers():\\n    assert add(-1, -1) == -2\\n"\n'
                '}'
            )
        )

        repo_info = RepositoryInfo(
            name="mock_repo",
            owner="testowner",
            url="https://github.com/testowner/mock_repo",
            default_branch="main",
        )

        generator = UnitTestGenerator(llm_generator=mock_llm)
        response = await generator.generate_tests(
            repo_path=repo_dir,
            repo_info=repo_info,
            file_path="calc.py",
            entity_name="add",
        )

        assert response.validation.syntax_valid is True
        assert response.validation.test_functions_found == 2
        assert len(response.test_cases) == 2
        assert "assert add(1, 2) == 3" in response.test_code


class TestTestGenerationAPIEndpoint:
    """Integration tests for POST /api/v1/repositories/generate-tests."""

    def test_generate_tests_invalid_url(self):
        response = client.post(
            "/api/v1/repositories/generate-tests",
            json={
                "repository_url": "invalid-url",
                "file_path": "app/service.py",
                "entity_name": "my_func",
            },
        )
        assert response.status_code == 400
        assert "HTTPS URLs are permitted" in response.json()["detail"]

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_generate_tests_successful_flow(self, mock_cloned_repo, tmp_path):
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()
        test_py = repo_dir / "service.py"
        test_py.write_text("def ping() -> str:\n    return 'pong'\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.__enter__.return_value = (repo_dir, "main")
        mock_context.__exit__.return_value = None
        mock_cloned_repo.return_value = mock_context

        response = client.post(
            "/api/v1/repositories/generate-tests",
            json={
                "repository_url": "https://github.com/owner/mock_repo",
                "file_path": "service.py",
                "entity_name": "ping",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["target"]["entity_name"] == "ping"
        assert data["framework"] == "pytest"
        assert data["validation"]["syntax_valid"] is True
        assert len(data["test_cases"]) >= 1
        assert "test_code" in data
        assert "ping" in data["test_code"]

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_generate_tests_entity_not_found(self, mock_cloned_repo, tmp_path):
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()
        test_py = repo_dir / "service.py"
        test_py.write_text("def other_func(): pass\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.__enter__.return_value = (repo_dir, "main")
        mock_context.__exit__.return_value = None
        mock_cloned_repo.return_value = mock_context

        response = client.post(
            "/api/v1/repositories/generate-tests",
            json={
                "repository_url": "https://github.com/owner/mock_repo",
                "file_path": "service.py",
                "entity_name": "nonexistent_func",
            },
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_generate_tests_file_not_found(self, mock_cloned_repo, tmp_path):
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()

        mock_context = MagicMock()
        mock_context.__enter__.return_value = (repo_dir, "main")
        mock_context.__exit__.return_value = None
        mock_cloned_repo.return_value = mock_context

        response = client.post(
            "/api/v1/repositories/generate-tests",
            json={
                "repository_url": "https://github.com/owner/mock_repo",
                "file_path": "missing.py",
                "entity_name": "any_func",
            },
        )

        assert response.status_code == 404
        assert "does not exist" in response.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_generate_tests_unsupported_language(self, mock_cloned_repo, tmp_path):
        repo_dir = tmp_path / "mock_repo"
        repo_dir.mkdir()
        js_file = repo_dir / "app.js"
        js_file.write_text("function test() {}", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.__enter__.return_value = (repo_dir, "main")
        mock_context.__exit__.return_value = None
        mock_cloned_repo.return_value = mock_context

        response = client.post(
            "/api/v1/repositories/generate-tests",
            json={
                "repository_url": "https://github.com/owner/mock_repo",
                "file_path": "app.js",
                "entity_name": "test",
            },
        )

        assert response.status_code == 400
        assert "supports python" in response.json()["detail"].lower()

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_generate_tests_repository_not_found(self, mock_cloned_repo):
        mock_cloned_repo.side_effect = RepositoryAccessError("Repository does not exist")
        response = client.post(
            "/api/v1/repositories/generate-tests",
            json={
                "repository_url": "https://github.com/owner/nonexistent",
                "file_path": "app.py",
                "entity_name": "test",
            },
        )
        assert response.status_code == 404

    @patch("app.api.v1.endpoints.repositories.RepositoryService.cloned_repository")
    def test_generate_tests_cloning_error(self, mock_cloned_repo):
        mock_cloned_repo.side_effect = RepositoryCloningError("Git clone failure")
        response = client.post(
            "/api/v1/repositories/generate-tests",
            json={
                "repository_url": "https://github.com/owner/fail-clone",
                "file_path": "app.py",
                "entity_name": "test",
            },
        )
        assert response.status_code == 502
