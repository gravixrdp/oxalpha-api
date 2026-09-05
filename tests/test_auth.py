"""Tests for API Key authentication on protected routes."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_auth_missing_header(client: httpx.AsyncClient):
    """Request without Authorization header should fail with 401."""
    response = await client.get("/v1/models")
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "invalid_api_key"
    assert "test-secret-key-123" not in response.text


@pytest.mark.asyncio
async def test_auth_invalid_bearer_format(client: httpx.AsyncClient):
    """Request with malformed Authorization header should fail with 401."""
    response = await client.get("/v1/models", headers={"Authorization": "Basic somecredentials"})
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "invalid_api_key"


@pytest.mark.asyncio
async def test_auth_wrong_api_key(client: httpx.AsyncClient):
    """Request with wrong API key should fail with 401."""
    response = await client.get("/v1/models", headers={"Authorization": "Bearer wrong-key-456"})
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "invalid_api_key"
    assert "wrong-key-456" not in response.text


@pytest.mark.asyncio
async def test_auth_success(client: httpx.AsyncClient, auth_headers: dict[str, str]):
    """Request with valid API key succeeds."""
    response = await client.get("/v1/models", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
