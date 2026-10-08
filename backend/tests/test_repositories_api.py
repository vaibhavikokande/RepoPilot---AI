"""Tests for the repository analysis API endpoint."""

from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.services.repository_service import (
    RepositoryAccessError,
    RepositoryCloningError,
)


def test_analyze_invalid_url(client: TestClient) -> None:
    """Request with an invalid URL should return HTTP 400."""
    response = client.post(
        "/api/v1/repositories/analyze",
        json={"repository_url": "not-a-valid-url"},
    )
    assert response.status_code == 400
    assert "Invalid" in response.json()["detail"] or "Only secure HTTPS" in response.json()["detail"]


def test_analyze_non_github_url(client: TestClient) -> None:
    """Request with a non-GitHub URL should return HTTP 400."""
    response = client.post(
        "/api/v1/repositories/analyze",
        json={"repository_url": "https://gitlab.com/owner/repo"},
    )
    assert response.status_code == 400
    assert "Only GitHub repositories are supported" in response.json()["detail"]


def test_analyze_successful_flow(
    client: TestClient, sample_repo_path: Path
) -> None:
    """Successful analysis should return complete repository metadata, statistics, and tree."""

    @contextmanager
    def mock_cloned_repository(self, clone_url: str, owner: str, name: str):
        yield sample_repo_path, "main"

    with patch(
        "app.services.repository_service.RepositoryService.cloned_repository",
        new=mock_cloned_repository,
    ):
        response = client.post(
            "/api/v1/repositories/analyze",
            json={"repository_url": "https://github.com/test-owner/test-repo"},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"

        # Check repository info
        repo = data["repository"]
        assert repo["name"] == "test-repo"
        assert repo["owner"] == "test-owner"
        assert repo["url"] == "https://github.com/test-owner/test-repo"
        assert repo["default_branch"] == "main"

        # Check statistics
        stats = data["statistics"]
        assert stats["total_files"] == 7
        assert stats["total_directories"] > 0
        assert stats["total_size_bytes"] > 0
        assert len(stats["largest_files"]) > 0

        # Check languages
        languages = data["languages"]
        assert "Python" in languages
        assert languages["Python"] == 3
        assert "TypeScript" in languages

        # Check file tree
        tree = data["file_tree"]
        assert isinstance(tree, list)
        tree_names = [node["name"] for node in tree]
        assert "app" in tree_names
        assert "README.md" in tree_names


def test_analyze_repository_not_found(client: TestClient) -> None:
    """Inaccessible/private repository should return HTTP 404."""

    @contextmanager
    def mock_not_found(self, clone_url: str, owner: str, name: str):
        raise RepositoryAccessError(
            "Unable to access this repository. Please make sure the repository is public and the URL is correct."
        )
        yield  # noqa: unreachable

    with patch(
        "app.services.repository_service.RepositoryService.cloned_repository",
        new=mock_not_found,
    ):
        response = client.post(
            "/api/v1/repositories/analyze",
            json={"repository_url": "https://github.com/nonexistent/private-repo"},
        )

        assert response.status_code == 404
        assert "Unable to access this repository" in response.json()["detail"]


def test_analyze_repository_cloning_network_failure(client: TestClient) -> None:
    """Cloning network failure should return HTTP 502."""

    @contextmanager
    def mock_network_error(self, clone_url: str, owner: str, name: str):
        raise RepositoryCloningError("Network error while connecting to GitHub.")
        yield  # noqa: unreachable

    with patch(
        "app.services.repository_service.RepositoryService.cloned_repository",
        new=mock_network_error,
    ):
        response = client.post(
            "/api/v1/repositories/analyze",
            json={"repository_url": "https://github.com/owner/repo"},
        )

        assert response.status_code == 502
        assert "Network error" in response.json()["detail"]
