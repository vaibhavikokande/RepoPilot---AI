"""Tests for POST /api/v1/repositories/analyze-code endpoint."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.repository_service import (
    RepositoryAccessError,
    RepositoryCloningError,
)


def test_analyze_code_invalid_url(client: TestClient) -> None:
    """Request with an invalid URL should return HTTP 400."""
    response = client.post(
        "/api/v1/repositories/analyze-code",
        json={"repository_url": "invalid-url"},
    )
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"] or "Only secure HTTPS" in response.json()["detail"]


def test_analyze_code_non_github_url(client: TestClient) -> None:
    """Request with a non-GitHub URL should return HTTP 400."""
    response = client.post(
        "/api/v1/repositories/analyze-code",
        json={"repository_url": "https://gitlab.com/owner/repo"},
    )
    assert response.status_code == 400
    assert "Only GitHub repositories are supported" in response.json()["detail"]


def test_analyze_code_successful_flow(
    client: TestClient, sample_repo_path: Path
) -> None:
    """Successful code analysis should return structured summary, entities, and codebase tree."""

    @contextmanager
    def mock_cloned_repository(self, clone_url: str, owner: str, name: str):
        yield sample_repo_path, "main"

    with patch(
        "app.services.repository_service.RepositoryService.cloned_repository",
        new=mock_cloned_repository,
    ):
        response = client.post(
            "/api/v1/repositories/analyze-code",
            json={"repository_url": "https://github.com/my-org/my-service"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"

        # Check repository metadata
        repo = data["repository"]
        assert repo["name"] == "my-service"
        assert repo["owner"] == "my-org"
        assert repo["url"] == "https://github.com/my-org/my-service"

        # Check summary metrics
        summary = data["summary"]
        assert summary["files_analyzed"] >= 3
        assert summary["classes"] >= 2
        assert summary["functions"] >= 2
        assert summary["methods"] >= 3
        assert summary["imports"] >= 3
        assert summary["files_with_errors"] == 0

        # Check entities
        entities = data["entities"]
        assert len(entities) > 0
        entity_names = [e["name"] for e in entities]
        assert "UserService" in entity_names
        assert "create_app" in entity_names

        # Check dependencies
        deps = data["dependencies"]
        assert isinstance(deps, list)

        # Check codebase tree
        tree = data["codebase_tree"]
        assert isinstance(tree, list)
        assert len(tree) > 0


def test_analyze_code_repository_not_found(client: TestClient) -> None:
    """Inaccessible/private repository should return HTTP 404."""

    @contextmanager
    def mock_not_found(self, clone_url: str, owner: str, name: str):
        raise RepositoryAccessError("Unable to access this repository.")
        yield  # noqa: unreachable

    with patch(
        "app.services.repository_service.RepositoryService.cloned_repository",
        new=mock_not_found,
    ):
        response = client.post(
            "/api/v1/repositories/analyze-code",
            json={"repository_url": "https://github.com/nonexistent/private-repo"},
        )

        assert response.status_code == 404
        assert "Unable to access this repository" in response.json()["detail"]


def test_analyze_code_repository_network_failure(client: TestClient) -> None:
    """Network failure during clone should return HTTP 502."""

    @contextmanager
    def mock_network_error(self, clone_url: str, owner: str, name: str):
        raise RepositoryCloningError("Network error while connecting to GitHub.")
        yield  # noqa: unreachable

    with patch(
        "app.services.repository_service.RepositoryService.cloned_repository",
        new=mock_network_error,
    ):
        response = client.post(
            "/api/v1/repositories/analyze-code",
            json={"repository_url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 502
        assert "Network error" in response.json()["detail"]
