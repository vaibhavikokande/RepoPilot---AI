"""API endpoints for documentation retrieval."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.doc_generator.store import document_store
from app.schemas.documentation import DocGenerateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documentation", tags=["Documentation"])


@router.get(
    "/{document_id}",
    response_model=DocGenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve previously generated technical documentation by ID",
)
def get_document(document_id: str) -> DocGenerateResponse:
    """Retrieve previously generated technical documentation session by document ID.

    Args:
        document_id: ID returned by the generate-docs endpoint.

    Returns:
        DocGenerateResponse with full Markdown content and metadata.
    """
    doc = document_store.get(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    return doc
