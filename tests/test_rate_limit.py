"""Tests for application-level rate limiting."""

import pytest
import httpx
from app.rate_limiter import get_rate_limiter


@pytest.mark.asyncio
async def test_rate_limiter_exceeded(client: httpx.AsyncClient, auth_headers: dict[str, str]):
    """Ensure exceeding requests within window triggers HTTP 429."""
    limiter = get_rate_limiter()
    limiter.requests_limit = 3
    limiter.window_seconds = 60

    # First 3 requests should pass authentication and reach endpoint
    for _ in range(3):
        res = await client.get("/v1/models", headers=auth_headers)
        assert res.status_code == 200

    # 4th request must be rejected with 429
    res = await client.get("/v1/models", headers=auth_headers)
    assert res.status_code == 429
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "rate_limit_exceeded"
    assert "Retry-After" in res.headers
