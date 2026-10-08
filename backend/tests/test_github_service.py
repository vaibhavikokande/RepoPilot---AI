"""Tests for GitHub URL validation and metadata parsing."""

import pytest

from app.services.github_service import (
    GitHubService,
    InvalidRepositoryURLError,
)


class TestGitHubServiceValidation:
    """Test suite for GitHubService URL validation."""

    def test_valid_urls(self) -> None:
        """Valid GitHub HTTPS URLs should be parsed correctly."""
        test_cases = [
            ("https://github.com/octocat/Hello-World", "octocat", "Hello-World"),
            ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World"),
            ("https://github.com/octocat/Hello-World/", "octocat", "Hello-World"),
            ("https://github.com/octocat/Hello-World.git/", "octocat", "Hello-World"),
            ("https://www.github.com/facebook/react", "facebook", "react"),
            ("https://github.com/langchain-ai/langgraph", "langchain-ai", "langgraph"),
            ("https://github.com/tiangolo/fastapi.git", "tiangolo", "fastapi"),
        ]

        for raw_url, expected_owner, expected_name in test_cases:
            parsed = GitHubService.validate_and_parse_url(raw_url)
            assert parsed.owner == expected_owner
            assert parsed.name == expected_name
            assert parsed.url == f"https://github.com/{expected_owner}/{expected_name}"
            assert parsed.clone_url == f"https://github.com/{expected_owner}/{expected_name}.git"

    def test_reject_non_https(self) -> None:
        """Insecure HTTP URLs must be rejected."""
        with pytest.raises(InvalidRepositoryURLError, match="Only secure HTTPS URLs"):
            GitHubService.validate_and_parse_url("http://github.com/owner/repo")

    def test_reject_non_github_domains(self) -> None:
        """Non-GitHub domains must be rejected."""
        invalid_hosts = [
            "https://gitlab.com/owner/repo",
            "https://bitbucket.org/owner/repo",
            "https://evil.com/owner/repo",
        ]
        for url in invalid_hosts:
            with pytest.raises(InvalidRepositoryURLError, match="Only GitHub repositories are supported"):
                GitHubService.validate_and_parse_url(url)

    def test_reject_credentials_in_url(self) -> None:
        """URLs containing credentials must be rejected for security."""
        with pytest.raises(InvalidRepositoryURLError, match="credentials"):
            GitHubService.validate_and_parse_url("https://user:token@github.com/owner/repo")

    def test_reject_empty_or_non_string(self) -> None:
        """Empty strings must be rejected."""
        with pytest.raises(InvalidRepositoryURLError, match="cannot be empty"):
            GitHubService.validate_and_parse_url("")

    def test_reject_incomplete_paths(self) -> None:
        """URLs missing owner or repository name must be rejected."""
        incomplete = [
            "https://github.com",
            "https://github.com/",
            "https://github.com/onlyowner",
            "https://github.com/owner/repo/extra/branch",
        ]
        for url in incomplete:
            with pytest.raises(InvalidRepositoryURLError):
                GitHubService.validate_and_parse_url(url)

    def test_reject_invalid_characters_and_injections(self) -> None:
        """Disallowed characters and injection attempts must be rejected."""
        bad_urls = [
            "https://github.com/owner/repo;rm -rf /",
            "https://github.com/owner/repo&&echo hi",
            "https://github.com/owner/`whoami`",
            "https://github.com/-invalid-/repo",
            "https://github.com/owner/..",
        ]
        for url in bad_urls:
            with pytest.raises(InvalidRepositoryURLError):
                GitHubService.validate_and_parse_url(url)
