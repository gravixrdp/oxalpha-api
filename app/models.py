"""OpenAI-compatible request and response schemas."""

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """Chat message object."""

    role: str
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None

    model_config = ConfigDict(extra="allow")


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request schema."""

    model: str
    messages: list[ChatMessage] = Field(..., min_length=1)
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    n: int | None = 1
    max_tokens: int | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    user: str | None = None

    model_config = ConfigDict(extra="allow")


class ChatMessageResponse(BaseModel):
    """Assistant message in completion response."""

    role: Literal["assistant"] = "assistant"
    content: str


class ChatCompletionChoice(BaseModel):
    """Choice item in completion response."""

    index: int = 0
    message: ChatMessageResponse
    finish_reason: str | None = "stop"


class UsageInfo(BaseModel):
    """Token usage info."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible non-streaming chat completion response."""

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo | None = None


class ChunkDelta(BaseModel):
    """Delta payload in streaming chunk choice."""

    role: str | None = None
    content: str | None = None

    model_config = ConfigDict(extra="allow")


class ChunkChoice(BaseModel):
    """Choice item in streaming chunk."""

    index: int = 0
    delta: ChunkDelta
    finish_reason: str | None = None

    model_config = ConfigDict(extra="allow")


class ChatCompletionChunk(BaseModel):
    """OpenAI-compatible chat completion chunk event."""

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]

    model_config = ConfigDict(extra="allow")


class ModelCard(BaseModel):
    """OpenAI model representation."""

    id: str
    object: Literal["model"] = "model"
    created: int = 1700000000
    owned_by: str = "oxalpha-proxy"


class ModelListResponse(BaseModel):
    """OpenAI-compatible model list response."""

    object: Literal["list"] = "list"
    data: list[ModelCard]


class ErrorDetail(BaseModel):
    """OpenAI-compatible error detail."""

    message: str
    type: str
    param: str | None = None
    code: str | None = None


class ErrorResponse(BaseModel):
    """OpenAI-compatible error response wrapper."""

    error: ErrorDetail
