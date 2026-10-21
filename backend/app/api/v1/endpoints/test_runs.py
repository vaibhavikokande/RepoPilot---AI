"""API endpoints for test run status and retrieval."""

import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.test_execution import SandboxStatus, TestRunResponse
from app.test_execution.runner import test_run_store
from app.test_execution.sandbox import get_sandbox_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test-runs", tags=["Test Execution"])


@router.get(
    "/sandbox-status",
    response_model=SandboxStatus,
    summary="Get container sandbox status and diagnostic information",
)
def read_sandbox_status() -> SandboxStatus:
    """Return diagnostic status of Docker container sandbox runtime on the server."""
    return get_sandbox_status()


@router.get(
    "/{run_id}",
    response_model=TestRunResponse,
    summary="Get status and results of a test execution run",
)
def get_test_run(run_id: str) -> TestRunResponse:
    """Retrieve test run outcome, summary, coverage, and logs for a given run ID.

    Args:
        run_id: UUID string returned by the test execution endpoint.

    Returns:
        TestRunResponse with full execution results.
    """
    run = test_run_store.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test run with ID '{run_id}' not found.",
        )
    return run
