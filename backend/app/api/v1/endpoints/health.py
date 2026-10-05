"""Health check endpoint for RepoPilot AI."""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.constants import APP_NAME, APP_VERSION

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str
    service: str
    version: str
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return the current health status of the RepoPilot AI service."""
    return HealthResponse(
        status="healthy",
        service=APP_NAME,
        version=APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
