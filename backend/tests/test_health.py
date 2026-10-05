"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient


def test_health_endpoint_returns_200(client: TestClient) -> None:
    """Health endpoint should return HTTP 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_endpoint_response_schema(client: TestClient) -> None:
    """Health response should contain all expected fields."""
    response = client.get("/api/v1/health")
    data = response.json()

    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data


def test_health_endpoint_values(client: TestClient) -> None:
    """Health response should return correct values."""
    response = client.get("/api/v1/health")
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "RepoPilot AI"
    assert data["version"] == "0.1.0"


def test_health_endpoint_content_type(client: TestClient) -> None:
    """Health endpoint should return JSON content type."""
    response = client.get("/api/v1/health")
    assert response.headers["content-type"] == "application/json"
