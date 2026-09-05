"""Logging utilities, request context, and SSE formatting."""

import contextvars
import json
import logging
import re
from typing import Any

# Context variable to hold request ID for the current async task
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id_ctx", default="-")

# Regex patterns to sanitize sensitive tokens if present in log messages
SENSITIVE_PATTERNS = [
    re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE),
    re.compile(r"(XSRF-TOKEN=)[^;\s]+", re.IGNORECASE),
    re.compile(r"(ox_alpha_session=)[^;\s]+", re.IGNORECASE),
    re.compile(r"(api[-_]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s,]+", re.IGNORECASE),
]


class RequestIdFilter(logging.Filter):
    """Injects current request ID into log records and scrubs sensitive values."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        if isinstance(record.msg, str):
            sanitized = record.msg
            for pattern in SENSITIVE_PATTERNS:
                sanitized = pattern.sub(r"\1[REDACTED]", sanitized)
            record.msg = sanitized
        return True


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("llm_proxy")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [req_id=%(request_id)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logger()


def format_sse_chunk(data: dict[str, Any]) -> str:
    """Format dictionary as Server-Sent Event data block."""
    return f"data: {json.dumps(data, ensure_ascii=False, separators=(',', ':'))}\n\n"


def format_sse_done() -> str:
    """Format standard OpenAI SSE termination signal."""
    return "data: [DONE]\n\n"
