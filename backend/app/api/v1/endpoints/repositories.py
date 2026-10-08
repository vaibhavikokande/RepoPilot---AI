"""Repository ingestion and analysis API endpoints."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.repository import (
    RepositoryAnalyzeRequest,
    RepositoryAnalyzeResponse,
    RepositoryInfo,
)
from app.services.github_service import (
    GitHubService,
    InvalidRepositoryURLError,
)
from app.services.repository_service import (
    RepositoryAccessError,
    RepositoryCloningError,
    RepositoryService,
)
from app.services.scanner_service import ScannerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["Repositories"])


@router.post(
    "/analyze",
    response_model=RepositoryAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a public GitHub repository",
    description=(
        "Validates the GitHub URL, performs a safe shallow clone into a temporary workspace, "
        "scans files, detects programming languages, calculates statistics, and returns a "
        "structured summary with a simplified file tree."
    ),
)
async def analyze_repository(
    request: RepositoryAnalyzeRequest,
) -> RepositoryAnalyzeResponse:
    """Analyze a public GitHub repository.

    Args:
        request: Request containing the public repository URL.

    Returns:
        RepositoryAnalyzeResponse with repository metadata, statistics, languages, and file tree.
    """
    settings = get_settings()

    # 1. Validate and parse the GitHub URL
    try:
        parsed_repo = GitHubService.validate_and_parse_url(request.repository_url)
    except InvalidRepositoryURLError as exc:
        logger.info("Invalid repository URL rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # 2. Clone and scan repository inside safe workspace
    repo_service = RepositoryService()

    try:
        with repo_service.cloned_repository(
            clone_url=parsed_repo.clone_url,
            owner=parsed_repo.owner,
            name=parsed_repo.name,
        ) as (repo_path, default_branch):
            # 3. Scan files, calculate statistics, and detect languages
            statistics, languages = ScannerService.scan_repository(repo_path)

            # 4. Generate structured file tree
            file_tree = ScannerService.generate_file_tree(
                repo_path=repo_path,
                max_depth=settings.max_file_tree_depth,
            )

            repo_info = RepositoryInfo(
                name=parsed_repo.name,
                owner=parsed_repo.owner,
                url=parsed_repo.url,
                default_branch=default_branch,
            )

            return RepositoryAnalyzeResponse(
                repository=repo_info,
                statistics=statistics,
                languages=languages,
                file_tree=file_tree,
                status="success",
            )

    except RepositoryAccessError as exc:
        logger.warning(
            "Repository access failed for %s: %s", parsed_repo.url, exc
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except RepositoryCloningError as exc:
        logger.error(
            "Repository cloning failed for %s: %s", parsed_repo.url, exc
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Unexpected error while analyzing repository: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred while analyzing the repository.",
        ) from exc
