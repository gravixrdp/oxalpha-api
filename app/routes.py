"""FastAPI route definitions for health, models, and completions."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import verify_api_key
from app.config import get_settings
from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ModelCard,
    ModelListResponse,
)
from app.rate_limiter import check_rate_limit
from app.upstream import get_upstream_client
from app.utils import request_id_ctx

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint. Publicly accessible without authentication."""
    return {"status": "ok"}


@router.get(
    "/v1/models",
    response_model=ModelListResponse,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
    tags=["Models"],
)
async def list_models() -> ModelListResponse:
    """List available models in OpenAI-compatible format."""
    settings = get_settings()
    models = [
        ModelCard(id=settings.PUBLIC_MODEL_NAME, owned_by="oxalpha-proxy"),
    ]
    if settings.UPSTREAM_MODEL != settings.PUBLIC_MODEL_NAME:
        models.append(ModelCard(id=settings.UPSTREAM_MODEL, owned_by="oxalpha-proxy"))

    return ModelListResponse(data=models)


@router.post(
    "/v1/chat/completions",
    response_model=None,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
    tags=["Chat"],
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    raw_request: Request,
) -> ChatCompletionResponse | StreamingResponse:
    """Create a chat completion (streaming or non-streaming).

    Fully compatible with OpenAI client specifications.
    """
    upstream_client = get_upstream_client()
    req_id = request_id_ctx.get()

    if request.stream:
        return StreamingResponse(
            upstream_client.stream_chat_completion(request, req_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "X-Request-ID": req_id,
            },
        )

    response = await upstream_client.create_chat_completion(request, req_id)
    return response
