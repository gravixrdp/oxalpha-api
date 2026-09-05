"""Tests for error handling, validation, timeouts, and payload limits."""

import pytest
import httpx

from app.upstream import get_upstream_client


@pytest.mark.asyncio
async def test_validation_error_missing_messages(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    """Request missing messages parameter should return 400 in OpenAI error format."""
    payload = {"model": "glm-5.3-flash"}
    res = await client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert "error" in data
    assert data["error"]["type"] == "invalid_request_error"
    assert data["error"]["code"] == "invalid_request"


@pytest.mark.asyncio
async def test_validation_error_empty_messages(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    """Request with empty messages array should return 400."""
    payload = {"model": "glm-5.3-flash", "messages": []}
    res = await client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    assert res.status_code == 400
    data = res.json()
    assert "error" in data
    assert data["error"]["type"] == "invalid_request_error"


@pytest.mark.asyncio
async def test_payload_too_large(client: httpx.AsyncClient, auth_headers: dict[str, str]):
    """Ensure payloads exceeding max body size are rejected with 413."""
    huge_text = "x" * (3 * 1024 * 1024)  # 3MB > 2MB limit
    payload = {
        "model": "glm-5.3-flash",
        "messages": [{"role": "user", "content": huge_text}],
    }
    headers = {**auth_headers, "Content-Length": str(len(huge_text))}
    res = await client.post("/v1/chat/completions", headers=headers, json=payload)
    assert res.status_code == 413
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "request_too_large"


@pytest.mark.asyncio
async def test_upstream_server_error_returns_502(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    """Ensure upstream 500 error returns 502 with clean JSON and no stack traces."""
    upstream = get_upstream_client()
    await upstream.start()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/chat":
            return httpx.Response(200, headers={"Set-Cookie": "XSRF-TOKEN=test; Path=/"})
        if request.url.path == "/api/chat":
            return httpx.Response(500, text="Internal Server Error on upstream")
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    upstream._client = mock_client

    payload = {
        "model": "glm-5.3-flash",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    res = await client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    assert res.status_code == 502
    data = res.json()
    assert "error" in data
    assert data["error"]["type"] == "upstream_error"
    # Ensure internal upstream stack trace is not exposed
    assert "Internal Server Error on upstream" not in data["error"]["message"]
