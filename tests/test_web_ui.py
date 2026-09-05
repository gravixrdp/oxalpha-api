"""Tests for Web Chat UI and static assets."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_serve_web_chat_index(client: httpx.AsyncClient):
    """Ensure GET / serves the HTML web chat interface."""
    res = await client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Gravix AI Chat" in res.text
    assert "What can I help you with?" in res.text


@pytest.mark.asyncio
async def test_serve_static_css(client: httpx.AsyncClient):
    """Ensure static CSS is accessible."""
    res = await client.get("/static/css/style.css")
    assert res.status_code == 200
    assert "--bg-main" in res.text


@pytest.mark.asyncio
async def test_serve_static_js(client: httpx.AsyncClient):
    """Ensure static JS is accessible."""
    res = await client.get("/static/js/app.js")
    assert res.status_code == 200
    assert "addEventListener" in res.text
