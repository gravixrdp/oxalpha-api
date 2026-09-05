"""Tests for the unauthenticated /health endpoint."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_health_check_success(client: httpx.AsyncClient):
    """Ensure /health returns 200 and status ok without authentication."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}
    assert "X-Request-ID" in response.headers
