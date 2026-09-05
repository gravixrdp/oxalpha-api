"""Tests for /v1/models endpoint."""

import pytest
import httpx


@pytest.mark.asyncio
async def test_list_models(client: httpx.AsyncClient, auth_headers: dict[str, str]):
    """Ensure models list returns OpenAI-compatible structure with configured models."""
    response = await client.get("/v1/models", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)

    model_ids = [m["id"] for m in data["data"]]
    assert "glm-5.3-flash" in model_ids
    assert "z-ai/glm-5.3-flash" in model_ids

    # Check structure of model card
    card = data["data"][0]
    assert card["object"] == "model"
    assert "created" in card
    assert card["owned_by"] == "oxalpha-proxy"
