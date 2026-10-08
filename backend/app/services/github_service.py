"""GitHub URL parsing and validation service."""

import re
from dataclasses import dataclass
from urllib.parse import urlparse


class InvalidRepositoryURLError(ValueError):
    """Raised when an invalid or disallowed repository URL is supplied."""


@dataclass(frozen=True)
class ParsedGitHubURL:
    """Validated and parsed GitHub repository URL metadata."""

    owner: str
    name: str
    url: str
    clone_url: str


# GitHub username: alphanumeric and hyphen, 1-39 chars, no start/end with hyphen
GITHUB_OWNER_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")
# GitHub repo name: alphanumeric, hyphens, underscores, dots, 1-100 chars (not '.' or '..')
GITHUB_REPO_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{1,100}$")


class GitHubService:
    """Service for validating and extracting GitHub repository metadata."""

    @staticmethod
    def validate_and_parse_url(raw_url: str) -> ParsedGitHubURL:
        """Validate and parse a GitHub repository URL.

        Args:
            raw_url: Candidate URL string.

        Returns:
            ParsedGitHubURL containing owner, name, clean URL, and clone URL.

        Raises:
            InvalidRepositoryURLError: If the URL is invalid, unsafe, or not a GitHub URL.
        """
        if not raw_url or not isinstance(raw_url, str):
            raise InvalidRepositoryURLError(
                "Repository URL cannot be empty. Please provide a valid GitHub HTTPS URL."
            )

        clean_url = raw_url.strip()

        # Parse URL
        try:
            parsed = urlparse(clean_url)
        except Exception as exc:
            raise InvalidRepositoryURLError(
                f"Malformed URL: {exc}"
            ) from exc

        # Only allow HTTPS protocol for security
        if parsed.scheme != "https":
            raise InvalidRepositoryURLError(
                "Only secure HTTPS URLs are permitted. Example: https://github.com/owner/repository"
            )

        # Disallow credentials in URL (e.g. https://user:pass@github.com/...)
        if parsed.username or parsed.password:
            raise InvalidRepositoryURLError(
                "URLs containing credentials or authentication tokens are not permitted."
            )

        # Disallow ports other than standard HTTPS (port 443 or default)
        if parsed.port and parsed.port != 443:
            raise InvalidRepositoryURLError(
                "Non-standard ports are not permitted for repository URLs."
            )

        # Host must strictly be github.com (or www.github.com)
        hostname = (parsed.hostname or "").lower()
        if hostname not in ("github.com", "www.github.com"):
            raise InvalidRepositoryURLError(
                f"Only GitHub repositories are supported at this stage. Found host: '{hostname or 'unknown'}'."
            )

        # Path must be of the form: /owner/repo (ignoring optional trailing slash / .git)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]

        if len(parts) != 2:
            raise InvalidRepositoryURLError(
                "Invalid repository path. Expected format: 'https://github.com/owner/repository'."
            )

        owner, repo_name = parts[0], parts[1]

        # Strip .git suffix if present
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        # Validate owner and repo names against GitHub standards
        if not GITHUB_OWNER_REGEX.match(owner):
            raise InvalidRepositoryURLError(
                f"Invalid GitHub owner name '{owner}'. Must contain only alphanumeric characters and hyphens."
            )

        if not GITHUB_REPO_REGEX.match(repo_name) or repo_name in (".", ".."):
            raise InvalidRepositoryURLError(
                f"Invalid GitHub repository name '{repo_name}'. Must contain only alphanumeric characters, underscores, hyphens, and periods."
            )

        canonical_url = f"https://github.com/{owner}/{repo_name}"
        clone_url = f"https://github.com/{owner}/{repo_name}.git"

        return ParsedGitHubURL(
            owner=owner,
            name=repo_name,
            url=canonical_url,
            clone_url=clone_url,
        )
