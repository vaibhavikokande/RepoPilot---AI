"""Aggregated router for all v1 API endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, repositories

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(repositories.router)
