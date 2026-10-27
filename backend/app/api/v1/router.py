"""Aggregated router for all v1 API endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import documentation, health, repositories, test_runs

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(repositories.router)
api_v1_router.include_router(test_runs.router)
api_v1_router.include_router(documentation.router)
