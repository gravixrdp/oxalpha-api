"""Pytest fixtures and test environment setup."""

import os
from typing import AsyncGenerator
import httpx
import pytest

# Configure test environment variables before importing app modules
os.environ["API_KEY"] = "test-secret-key-123"
os.environ["RATE_LIMIT_REQUESTS"] = "10"
os.environ["RATE_LIMIT_WINDOW"] = "10"
os.environ["UPSTREAM_URL"] = "https://mock-oxalpha.com"
os.environ["UPSTREAM_MODEL"] = "z-ai/glm-5.3-flash"
os.environ["PUBLIC_MODEL_NAME"] = "glm-5.3-flash"

from app.config import get_settings
from app.main import create_app
from app.rate_limiter import get_rate_limiter
from app.upstream import get_upstream_client


@pytest.fixture(autouse=True)
def reset_state():
    """Reset singletons and caches between tests."""
    get_settings.cache_clear()
    rate_limiter = get_rate_limiter()
    rate_limiter._records.clear()
    rate_limiter.requests_limit = 10
    rate_limiter.window_seconds = 10

    upstream = get_upstream_client()
    upstream._session_initialized = False
    upstream._xsrf_token = None


@pytest.fixture
def app_instance():
    """Create test FastAPI application."""
    test_app = create_app()
    return test_app


@pytest.fixture
async def client(app_instance) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an httpx AsyncClient targeting the test application via ASGITransport."""
    transport = httpx.ASGITransport(app=app_instance)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Valid authentication headers."""
    return {"Authorization": "Bearer test-secret-key-123"}
