"""Test configuration and shared fixtures."""

import shutil
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Provide a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def sample_repo_path() -> Generator[Path, None, None]:
    """Create a temporary directory structure mimicking a real repository."""
    temp_dir = Path(tempfile.mkdtemp(prefix="repopilot_test_repo_"))

    try:
        # Create standard directories and files
        app_dir = temp_dir / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "main.py").write_text(
            '"""Main application entry point."""\n'
            "import os\n"
            "from app.services import UserService\n\n"
            'APP_NAME = "SampleApp"\n\n'
            "def create_app() -> str:\n"
            '    """Create application instance."""\n'
            "    service = UserService()\n"
            "    return service.get_status()\n",
            encoding="utf-8",
        )
        (app_dir / "services.py").write_text(
            '"""Service layer."""\n'
            "from typing import Optional\n\n"
            "class UserService:\n"
            '    """Manages user operations."""\n'
            "    def __init__(self, db_url: Optional[str] = None):\n"
            "        self.db_url = db_url\n\n"
            "    def get_status(self) -> str:\n"
            '        """Return service status."""\n'
            '        return "ready"\n\n'
            "    def create_user(self, name: str) -> dict:\n"
            '        return {"name": name}\n',
            encoding="utf-8",
        )

        frontend_dir = temp_dir / "frontend"
        frontend_dir.mkdir(parents=True, exist_ok=True)
        (frontend_dir / "index.ts").write_text(
            "import { config } from './config';\n\n"
            "export interface UserProfile {\n"
            "  id: number;\n"
            "  name: string;\n"
            "}\n\n"
            "export class UserClient {\n"
            "  getUser(): UserProfile {\n"
            "    return { id: 1, name: 'Alice' };\n"
            "  }\n"
            "}\n\n"
            "export function render(): void {\n"
            "  console.log('Rendering');\n"
            "}\n",
            encoding="utf-8",
        )
        (frontend_dir / "style.css").write_text("body { color: red; }", encoding="utf-8")

        tests_dir = temp_dir / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_main.py").write_text(
            "import pytest\n"
            "from app.main import create_app\n\n"
            "def test_create_app():\n"
            '    assert create_app() == "ready"\n',
            encoding="utf-8",
        )

        (temp_dir / "README.md").write_text("# Test Project", encoding="utf-8")
        (temp_dir / "Dockerfile").write_text("FROM python:3.11", encoding="utf-8")

        # Create directories that should be IGNORED
        git_dir = temp_dir / ".git"
        git_dir.mkdir(parents=True, exist_ok=True)
        (git_dir / "config").write_text("[core]", encoding="utf-8")

        node_modules = temp_dir / "node_modules" / "some_pkg"
        node_modules.mkdir(parents=True, exist_ok=True)
        (node_modules / "pkg.js").write_text("module.exports = {};", encoding="utf-8")

        pycache_dir = app_dir / "__pycache__"
        pycache_dir.mkdir(parents=True, exist_ok=True)
        (pycache_dir / "main.cpython-313.pyc").write_bytes(b"\x00\x01\x02")

        # Create binary/media files that should be IGNORED
        (temp_dir / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (temp_dir / "archive.zip").write_bytes(b"PK\x03\x04")

        yield temp_dir

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
