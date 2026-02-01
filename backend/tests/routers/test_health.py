"""
Tests for health check endpoints.
"""
import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_health_live(self, client: AsyncClient):
        """Test liveness probe."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_ready(self, client: AsyncClient):
        """Test readiness probe."""
        response = await client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        # Database check may vary in test environment
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert data["status"] == "running"
        assert "docs" in data
