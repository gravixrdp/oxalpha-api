"""Tests for /v1/chat/completions endpoint (streaming, non-streaming, and 428 retry)."""

import json
import pytest
import httpx

from app.upstream import get_upstream_client


@pytest.mark.asyncio
async def test_non_streaming_completion(client: httpx.AsyncClient, auth_headers: dict[str, str]):
    """Test non-streaming completion aggregates SSE chunks into a single JSON response."""
    upstream = get_upstream_client()
    await upstream.start()

    # Mock upstream responses
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/chat":
            return httpx.Response(
                200,
                text="<html>chat page</html>",
                headers={"Set-Cookie": "XSRF-TOKEN=test-csrf-token%3D; Path=/"},
            )
        if request.url.path == "/api/chat":
            # Verify upstream request headers
            assert request.headers.get("x-xsrf-token") == "test-csrf-token="
            assert request.headers.get("x-context-sent") == "4"

            # Return SSE stream with 2 chunks + DONE
            chunk1 = {
                "id": "chatcmpl-test-01",
                "object": "chat.completion.chunk",
                "created": 1700000000,
                "model": "z-ai/glm-5.3-flash",
                "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hello, "}, "finish_reason": None}],
            }
            chunk2 = {
                "id": "chatcmpl-test-01",
                "object": "chat.completion.chunk",
                "created": 1700000000,
                "model": "z-ai/glm-5.3-flash",
                "choices": [{"index": 0, "delta": {"content": "world!"}, "finish_reason": "stop"}],
            }
            sse_content = (
                f"data: {json.dumps(chunk1)}\n\n"
                f"data: {json.dumps(chunk2)}\n\n"
                "data: [DONE]\n\n"
            )
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream; charset=utf-8"},
                text=sse_content,
            )
        return httpx.Response(404)

    # Attach MockTransport to upstream client
    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    upstream._client = mock_client

    payload = {
        "model": "glm-5.3-flash",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }

    res = await client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["object"] == "chat.completion"
    assert data["model"] == "glm-5.3-flash"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] == "Hello, world!"
    assert data["choices"][0]["finish_reason"] == "stop"


@pytest.mark.asyncio
async def test_streaming_completion(client: httpx.AsyncClient, auth_headers: dict[str, str]):
    """Test streaming completion returns OpenAI-compatible SSE events and [DONE]."""
    upstream = get_upstream_client()
    await upstream.start()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/chat":
            return httpx.Response(
                200,
                text="<html>chat page</html>",
                headers={"Set-Cookie": "XSRF-TOKEN=stream-token; Path=/"},
            )
        if request.url.path == "/api/chat":
            chunk = {
                "id": "chatcmpl-stream-01",
                "object": "chat.completion.chunk",
                "created": 1700000000,
                "model": "z-ai/glm-5.3-flash",
                "choices": [{"index": 0, "delta": {"content": "Streaming response"}, "finish_reason": None}],
            }
            sse_content = f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n"
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream; charset=utf-8"},
                text=sse_content,
            )
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    upstream._client = mock_client

    payload = {
        "model": "glm-5.3-flash",
        "messages": [{"role": "user", "content": "Stream test"}],
        "stream": True,
    }

    res = await client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    body = res.text
    assert "data: " in body
    chunks = [
        json.loads(line[6:])
        for line in body.split("\n\n")
        if line.startswith("data: ") and line.strip() != "data: [DONE]" and line.strip()
    ]
    full_content = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert "Streaming response" in full_content
    assert "data: [DONE]" in body


@pytest.mark.asyncio
async def test_428_precondition_required_retry_success(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    """Ensure HTTP 428 triggers session refresh and retries once successfully."""
    upstream = get_upstream_client()
    await upstream.start()

    attempt = 0
    refresh_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempt, refresh_count
        if request.url.path == "/chat":
            refresh_count += 1
            return httpx.Response(
                200,
                text="<html>chat page</html>",
                headers={"Set-Cookie": f"XSRF-TOKEN=token-v{refresh_count}; Path=/"},
            )
        if request.url.path == "/api/chat":
            attempt += 1
            if attempt == 1:
                # First attempt returns 428 Precondition Required
                return httpx.Response(428, text="Precondition Required")
            # Second attempt succeeds
            chunk = {
                "id": "chatcmpl-retry-01",
                "object": "chat.completion.chunk",
                "created": 1700000000,
                "model": "z-ai/glm-5.3-flash",
                "choices": [{"index": 0, "delta": {"content": "Success after 428 retry!"}, "finish_reason": "stop"}],
            }
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream; charset=utf-8"},
                text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n",
            )
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    upstream._client = mock_client

    payload = {
        "model": "glm-5.3-flash",
        "messages": [{"role": "user", "content": "Test 428"}],
        "stream": False,
    }

    res = await client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["choices"][0]["message"]["content"] == "Success after 428 retry!"
    assert attempt == 2
    assert refresh_count >= 2


@pytest.mark.asyncio
async def test_428_double_failure_returns_502(
    client: httpx.AsyncClient, auth_headers: dict[str, str]
):
    """Ensure HTTP 428 returning twice fails with 502 Bad Gateway without infinite retry."""
    upstream = get_upstream_client()
    await upstream.start()

    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        if request.url.path == "/chat":
            return httpx.Response(
                200,
                text="<html>chat page</html>",
                headers={"Set-Cookie": "XSRF-TOKEN=test-token; Path=/"},
            )
        if request.url.path == "/api/chat":
            call_count += 1
            return httpx.Response(428, text="Precondition Required")
        return httpx.Response(404)

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    upstream._client = mock_client

    payload = {
        "model": "glm-5.3-flash",
        "messages": [{"role": "user", "content": "Test 428 loop"}],
        "stream": False,
    }

    res = await client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    assert res.status_code == 502
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "upstream_precondition_failed"
    # Ensure it only attempted twice (initial + 1 retry, no infinite loop)
    assert call_count == 2
