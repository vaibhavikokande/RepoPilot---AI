"""Repository cloning and lifecycle management service."""

import logging
import os
import shutil
import stat
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional, Tuple

import git
from git.exc import GitCommandError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RepositoryServiceError(Exception):
    """Base exception for repository operations."""


class RepositoryAccessError(RepositoryServiceError):
    """Raised when a repository cannot be accessed, cloned, or found."""


class RepositoryCloningError(RepositoryServiceError):
    """Raised when an error occurs during repository cloning."""


class RepositoryService:
    """Service managing Git repository cloning and workspace lifecycle."""

    def __init__(self, workspace_root: Optional[Path] = None):
        settings = get_settings()
        if workspace_root:
            self.workspace_root = Path(workspace_root).resolve()
        else:
            # Anchor workspace to backend root or configured path
            backend_root = Path(__file__).resolve().parent.parent.parent
            self.workspace_root = (backend_root / settings.workspace_dir).resolve()

        # Ensure base workspace directory exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _generate_target_dir(self, owner: str, name: str) -> Path:
        """Create a unique, safe directory path within the workspace."""
        safe_prefix = f"{owner}_{name}_{uuid.uuid4().hex[:8]}"
        target_path = (self.workspace_root / safe_prefix).resolve()

        # Security check: Ensure target path is strictly within workspace_root (anti-traversal)
        try:
            target_path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise RepositoryServiceError(
                "Security violation: Target directory escapes workspace boundary."
            ) from exc

        return target_path

    @contextmanager
    def cloned_repository(
        self,
        clone_url: str,
        owner: str,
        name: str,
    ) -> Generator[Tuple[Path, Optional[str]], None, None]:
        """Clone a repository shallowly, yield its directory and default branch, then clean up.

        Args:
            clone_url: HTTPS clone URL for GitHub.
            owner: Repository owner.
            name: Repository name.

        Yields:
            Tuple of (cloned_repo_path, default_branch_name).

        Raises:
            RepositoryAccessError: If repo is private or doesn't exist.
            RepositoryCloningError: If an error happens while cloning.
        """
        target_dir = self._generate_target_dir(owner, name)
        repo: Optional[git.Repo] = None

        logger.info("Cloning repository %s into %s", clone_url, target_dir)

        try:
            # Perform a shallow clone (depth=1) for speed and minimal disk usage
            # Set GIT_TERMINAL_PROMPT=0 so Git doesn't hang prompting for password on private repos
            env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

            repo = git.Repo.clone_from(
                clone_url,
                str(target_dir),
                depth=1,
                multi_options=["--single-branch"],
                env=env,
            )

            # Determine default branch
            default_branch: Optional[str] = None
            try:
                default_branch = repo.active_branch.name
            except Exception:
                # Fallback to inspecting HEAD or branches
                try:
                    default_branch = repo.head.reference.name
                except Exception:
                    default_branch = None

            yield target_dir, default_branch

        except GitCommandError as exc:
            err_output = str(exc.stderr or exc.stdout or exc)
            logger.warning("Git clone failed for %s: %s", clone_url, err_output)

            # Check common failure scenarios
            if any(
                phrase in err_output.lower()
                for phrase in (
                    "authentication failed",
                    "not found",
                    "could not read username",
                    "terminal prompts disabled",
                    "repository not found",
                )
            ):
                raise RepositoryAccessError(
                    "Unable to access this repository. Please make sure the repository is public and the URL is correct."
                ) from exc

            if any(
                phrase in err_output.lower()
                for phrase in (
                    "could not resolve host",
                    "failed to connect",
                    "timed out",
                    "network is unreachable",
                )
            ):
                raise RepositoryCloningError(
                    "Network error while connecting to GitHub. Please check network connectivity and try again."
                ) from exc

            raise RepositoryCloningError(
                f"Failed to clone repository: {err_output.strip() or 'Unknown Git error.'}"
            ) from exc

        except Exception as exc:
            logger.error("Unexpected error cloning %s: %s", clone_url, exc)
            raise RepositoryCloningError(
                "An unexpected error occurred while processing the repository."
            ) from exc

        finally:
            # Close git repo object so file handles are released (crucial on Windows/Unix)
            if repo is not None:
                try:
                    repo.close()
                except Exception:
                    pass

            # Safe, thorough cleanup of the cloned directory
            self._force_remove_tree(target_dir)

    @staticmethod
    def _force_remove_tree(target_dir: Path) -> None:
        """Thoroughly remove a directory tree, resolving read-only flags and locked files."""
        if not target_dir.exists():
            return

        for root, dirs, files in os.walk(target_dir, topdown=False):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                try:
                    os.chmod(file_path, stat.S_IWRITE | stat.S_IWUSR)
                    os.unlink(file_path)
                except Exception:
                    pass

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    os.chmod(dir_path, stat.S_IWRITE | stat.S_IWUSR | stat.S_IXUSR)
                    os.rmdir(dir_path)
                except Exception:
                    pass

        try:
            os.rmdir(target_dir)
            logger.debug("Cleaned up workspace at %s", target_dir)
        except Exception:
            try:
                shutil.rmtree(target_dir, ignore_errors=True)
            except Exception as exc:
                logger.warning("Failed to clean up %s: %s", target_dir, exc)
