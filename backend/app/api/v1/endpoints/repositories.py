"""Repository ingestion and analysis API endpoints."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.code_intelligence import (
    CodeChunker,
    CodeIntelligenceAnalyzer,
    CodeSearchEngine,
    HybridCodeSearchService,
)
from app.core.config import get_settings
from app.embeddings import EmbeddingService
from app.schemas.code_analysis import (
    CodeAnalysisRequest,
    CodeAnalysisResponse,
)
from app.schemas.code_search import (
    CodeSearchRequest,
    CodeSearchResponse,
    CodeSearchResultItem,
    RepositoryIndexRequest,
    RepositoryIndexResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResultItem,
)
from app.schemas.repository import (
    RepositoryAnalyzeRequest,
    RepositoryAnalyzeResponse,
    RepositoryInfo,
)
from app.vector_store import ChromaVectorStore
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


@router.post(
    "/index",
    response_model=RepositoryIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Index repository code chunks into vector store",
    description=(
        "Clones the repository, statically analyzes AST entities, chunks code units, "
        "computes dense embeddings using configured model, and persists vectors and metadata "
        "in ChromaDB with repository-level isolation."
    ),
)
async def index_repository(
    request: RepositoryIndexRequest,
) -> RepositoryIndexResponse:
    """Index repository code chunks into the persistent vector store.

    Args:
        request: Repository URL and optional force_reindex flag.

    Returns:
        RepositoryIndexResponse with indexing statistics and vector dimensions.
    """
    # 1. Validate GitHub URL
    try:
        parsed_repo = GitHubService.validate_and_parse_url(request.repository_url)
    except InvalidRepositoryURLError as exc:
        logger.info("Invalid repository URL rejected for indexing: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # 2. Clone, chunk, embed, and persist vectors
    repo_service = RepositoryService()
    analyzer = CodeIntelligenceAnalyzer()
    chunker = CodeChunker()
    embedding_service = EmbeddingService()
    vector_store = ChromaVectorStore()

    try:
        with repo_service.cloned_repository(
            clone_url=parsed_repo.clone_url,
            owner=parsed_repo.owner,
            name=parsed_repo.name,
        ) as (repo_path, default_branch):
            _, files, _, _, _, _ = analyzer.analyze_repository(repo_path)
            chunks = chunker.chunk_repository(repo_path=repo_path, code_files=files)

            if not chunks:
                return RepositoryIndexResponse(
                    repository=RepositoryInfo(
                        name=parsed_repo.name,
                        owner=parsed_repo.owner,
                        url=parsed_repo.url,
                        default_branch=default_branch,
                    ),
                    status="success",
                    files_processed=len(files),
                    chunks_indexed=0,
                    chunks_skipped=0,
                    embedding_model=embedding_service.model_name,
                    dimension=embedding_service.dimension,
                    total_vectors_in_index=0,
                    message="Repository contains no parseable code chunks to index.",
                )

            # Generate embeddings in batches
            embeddings = await embedding_service.embed_chunks(chunks)

            # Persist in ChromaDB collection
            index_metrics = vector_store.index_chunks(
                repo_url=parsed_repo.url,
                chunks=chunks,
                embeddings=embeddings,
                embedding_model=embedding_service.model_name,
                dimension=embedding_service.dimension,
                force_reindex=request.force_reindex,
            )

            repo_info = RepositoryInfo(
                name=parsed_repo.name,
                owner=parsed_repo.owner,
                url=parsed_repo.url,
                default_branch=default_branch,
            )

            return RepositoryIndexResponse(
                repository=repo_info,
                status="success",
                files_processed=len(files),
                chunks_indexed=len(chunks),
                chunks_skipped=0,
                embedding_model=embedding_service.model_name,
                dimension=embedding_service.dimension,
                total_vectors_in_index=index_metrics.get("total_chunks", len(chunks)),
                message="Repository successfully indexed into persistent vector store.",
            )

    except RepositoryAccessError as exc:
        logger.warning("Repository access failed for %s: %s", parsed_repo.url, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RepositoryCloningError as exc:
        logger.error("Repository cloning failed for %s: %s", parsed_repo.url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error while indexing repository: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred while indexing the repository.",
        ) from exc


@router.post(
    "/semantic-search",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic and hybrid code search using vector similarity and rank fusion",
    description=(
        "Retrieves relevant code chunks using vector embeddings, keyword relevance, or hybrid RRF fusion. "
        "Automatically checks or builds the repository vector index if not yet present."
    ),
)
async def semantic_search_repository(
    request: SemanticSearchRequest,
) -> SemanticSearchResponse:
    """Perform semantic or hybrid search across indexed repository code chunks.

    Args:
        request: Natural language query, repository URL, limit, entity_types, and search mode.

    Returns:
        SemanticSearchResponse containing matching code entities, snippets, line numbers, and scores.
    """
    # 1. Validate GitHub URL
    try:
        parsed_repo = GitHubService.validate_and_parse_url(request.repository_url)
    except InvalidRepositoryURLError as exc:
        logger.info("Invalid repository URL rejected: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    repo_service = RepositoryService()
    analyzer = CodeIntelligenceAnalyzer()
    chunker = CodeChunker()
    embedding_service = EmbeddingService()
    vector_store = ChromaVectorStore()
    hybrid_search = HybridCodeSearchService(
        embedding_service=embedding_service,
        vector_store=vector_store,
    )

    try:
        # Check if vector index exists; if not or if lexical/hybrid requires in-memory chunks, clone repository
        index_exists = vector_store.collection_exists(parsed_repo.url)
        needs_chunks = (request.mode.lower() in ("lexical", "hybrid")) or (not index_exists)

        chunks = None
        default_branch = None

        if needs_chunks:
            with repo_service.cloned_repository(
                clone_url=parsed_repo.clone_url,
                owner=parsed_repo.owner,
                name=parsed_repo.name,
            ) as (repo_path, branch):
                default_branch = branch
                _, files, _, _, _, _ = analyzer.analyze_repository(repo_path)
                chunks = chunker.chunk_repository(repo_path=repo_path, code_files=files)

                # If collection was missing, index the chunks now
                if not index_exists and chunks:
                    embeddings = await embedding_service.embed_chunks(chunks)
                    vector_store.index_chunks(
                        repo_url=parsed_repo.url,
                        chunks=chunks,
                        embeddings=embeddings,
                        embedding_model=embedding_service.model_name,
                        dimension=embedding_service.dimension,
                    )

        # Run search via hybrid search service
        raw_hits = await hybrid_search.search(
            repo_url=parsed_repo.url,
            query=request.query,
            chunks=chunks,
            mode=request.mode,
            limit=request.limit,
            entity_types=request.entity_types,
        )

        results = [
            SemanticSearchResultItem(
                chunk_id=hit["chunk_id"],
                file_path=hit["file_path"],
                entity_name=hit["entity_name"],
                entity_type=hit["entity_type"],
                language=hit["language"],
                start_line=hit["start_line"],
                end_line=hit["end_line"],
                signature=hit["signature"],
                docstring=hit["docstring"],
                parent=hit["parent"],
                code_snippet=hit["code_snippet"],
                context_header=hit["context_header"],
                tokens_estimate=hit["tokens_estimate"],
                score=hit["score"],
                search_mode=hit["search_mode"],
                match_reasons=hit["match_reasons"],
                explanation=hit["explanation"],
            )
            for hit in raw_hits
        ]

        repo_info = RepositoryInfo(
            name=parsed_repo.name,
            owner=parsed_repo.owner,
            url=parsed_repo.url,
            default_branch=default_branch,
        )

        return SemanticSearchResponse(
            repository=repo_info,
            query=request.query,
            search_mode=request.mode,
            total_results=len(results),
            results=results,
            status="success",
        )

    except RepositoryAccessError as exc:
        logger.warning("Repository access failed for %s: %s", parsed_repo.url, exc)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except RepositoryCloningError as exc:
        logger.error("Repository cloning failed for %s: %s", parsed_repo.url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during semantic search: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal error occurred during semantic search.",
        ) from exc



