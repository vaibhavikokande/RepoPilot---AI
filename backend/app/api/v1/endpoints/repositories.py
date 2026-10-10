"""Repository ingestion and analysis API endpoints."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.code_intelligence import (
    CodeChunker,
    CodeIntelligenceAnalyzer,
    CodeSearchEngine,
)
from app.core.config import get_settings
from app.schemas.code_analysis import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
)
from app.schemas.code_search import (
    CodeSearchRequest,
    CodeSearchResponse,
    CodeSearchResultItem,
)
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


@router.post(
    "/analyze-code",
    response_model=CodeAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Perform static code intelligence analysis on a repository",
    description=(
        "Clones the repository into an ephemeral workspace, statically parses supported "
        "source files (Python, JavaScript, TypeScript) using language ASTs, extracts classes, "
        "functions, methods, imports, dependencies, and builds a hierarchical codebase map."
    ),
)
async def analyze_repository_code(
    request: CodeAnalysisRequest,
) -> CodeAnalysisResponse:
    """Analyze source code structure and extract entities from a public repository.

    Args:
        request: Request containing the public repository URL.

    Returns:
        CodeAnalysisResponse with entities, dependencies, codebase map, and summary metrics.
    """
    # 1. Validate and parse the GitHub URL
    try:
        parsed_repo = GitHubService.validate_and_parse_url(request.repository_url)
    except InvalidRepositoryURLError as exc:
        logger.info("Invalid repository URL rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # 2. Clone and analyze code inside safe workspace
    repo_service = RepositoryService()
    analyzer = CodeIntelligenceAnalyzer()

    try:
        with repo_service.cloned_repository(
            clone_url=parsed_repo.clone_url,
            owner=parsed_repo.owner,
            name=parsed_repo.name,
        ) as (repo_path, default_branch):
            (
                summary,
                files,
                entities,
                dependencies,
                codebase_tree,
                errors,
            ) = analyzer.analyze_repository(repo_path)

            repo_info = RepositoryInfo(
                name=parsed_repo.name,
                owner=parsed_repo.owner,
                url=parsed_repo.url,
                default_branch=default_branch,
            )

            return CodeAnalysisResponse(
                repository=repo_info,
                summary=summary,
                files=files,
                entities=entities,
                dependencies=dependencies,
                codebase_tree=codebase_tree,
                errors=errors,
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
        logger.exception("Unexpected error while analyzing repository code: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred while analyzing the repository code.",
        ) from exc


@router.post(
    "/search-code",
    response_model=CodeSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search repository code using lexical and AST metadata analysis",
    description=(
        "Clones the repository into an ephemeral workspace, statically parses and extracts "
        "code chunks, indexes them with CodeChunker, and performs ranked lexical and metadata "
        "search with human-readable match explanations."
    ),
)
async def search_repository_code(
    request: CodeSearchRequest,
) -> CodeSearchResponse:
    """Perform keyword and metadata-driven search across indexed repository code chunks.

    Args:
        request: Search parameters including repository URL, query string, limit, and optional type filters.

    Returns:
        CodeSearchResponse containing matching code chunks, line numbers, snippets, and explanations.
    """
    # 1. Validate and parse the GitHub URL
    try:
        parsed_repo = GitHubService.validate_and_parse_url(request.repository_url)
    except InvalidRepositoryURLError as exc:
        logger.info("Invalid repository URL rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # 2. Clone, analyze code, chunk, and execute search in safe workspace
    repo_service = RepositoryService()
    analyzer = CodeIntelligenceAnalyzer()
    chunker = CodeChunker()

    try:
        with repo_service.cloned_repository(
            clone_url=parsed_repo.clone_url,
            owner=parsed_repo.owner,
            name=parsed_repo.name,
        ) as (repo_path, default_branch):
            # Parse repository files and entities
            _, files, _, _, _, _ = analyzer.analyze_repository(repo_path)

            # Generate semantic chunks
            chunks = chunker.chunk_repository(repo_path=repo_path, code_files=files)

            # Execute search
            search_engine = CodeSearchEngine(chunks=chunks)
            raw_results = search_engine.search(
                query=request.query,
                limit=request.limit,
                entity_types=request.entity_types,
            )

            # Format results
            result_items = [
                CodeSearchResultItem(
                    chunk_id=item["chunk"].chunk_id,
                    file_path=item["chunk"].file_path,
                    entity_name=item["chunk"].entity_name,
                    entity_type=item["chunk"].entity_type,
                    language=item["chunk"].language,
                    start_line=item["chunk"].start_line,
                    end_line=item["chunk"].end_line,
                    signature=item["chunk"].signature,
                    docstring=item["chunk"].docstring,
                    parent=item["chunk"].parent,
                    parameters=item["chunk"].parameters,
                    return_type=item["chunk"].return_type,
                    code_snippet=item["chunk"].code_content,
                    context_header=item["chunk"].context_header,
                    tokens_estimate=item["chunk"].tokens_estimate,
                    score=item["score"],
                    match_reasons=item["match_reasons"],
                    explanation=item["explanation"],
                )
                for item in raw_results
            ]

            repo_info = RepositoryInfo(
                name=parsed_repo.name,
                owner=parsed_repo.owner,
                url=parsed_repo.url,
                default_branch=default_branch,
            )

            return CodeSearchResponse(
                repository=repo_info,
                query=request.query,
                total_chunks_indexed=len(chunks),
                total_results=len(result_items),
                results=result_items,
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
        logger.exception("Unexpected error while searching repository code: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred while searching the repository code.",
        ) from exc


