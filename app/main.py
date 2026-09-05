"""FastAPI application entrypoint, lifecycle management, middleware, and error handlers."""

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.routes import router
from app.upstream import UpstreamError, get_upstream_client
from app.utils import logger, request_id_ctx


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: initialize upstream client and close on shutdown."""
    settings = get_settings()
    logger.info("Initializing Ox Alpha upstream HTTP client...")
    upstream_client = get_upstream_client()
    await upstream_client.start()
    logger.info(f"LLM Proxy service started. Public model: {settings.PUBLIC_MODEL_NAME}")

    yield

    logger.info("Shutting down Ox Alpha upstream HTTP client...")
    await upstream_client.close()
    logger.info("LLM Proxy service stopped.")


class RequestContextAndLogMiddleware(BaseHTTPMiddleware):
    """Middleware for Request ID generation, access logging, and sensitive data protection."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:16]}"
        token = request_id_ctx.set(req_id)

        start_time = time.monotonic()
        client_host = request.client.host if request.client else "unknown"

        # Log request start (without headers or body content)
        logger.info(f"--> {request.method} {request.url.path} from {client_host}")

        try:
            response = await call_next(request)
            duration_ms = (time.monotonic() - start_time) * 1000.0
            response.headers["X-Request-ID"] = req_id

            # Log request completion
            logger.info(
                f"<-- {request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)"
            )
            return response
        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000.0
            logger.error(
                f"<-- {request.method} {request.url.path} - EXCEPTION: {exc.__class__.__name__} ({duration_ms:.2f}ms)"
            )
            raise
        finally:
            request_id_ctx.reset(token)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing maximum incoming request body size."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        settings = get_settings()

        if content_length:
            try:
                length = int(content_length)
                if length > settings.MAX_REQUEST_BODY_SIZE:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error": {
                                "message": f"Request body exceeds maximum size of {settings.MAX_REQUEST_BODY_SIZE} bytes.",
                                "type": "invalid_request_error",
                                "param": None,
                                "code": "request_too_large",
                            }
                        },
                    )
            except ValueError:
                pass

        return await call_next(request)


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="Ox Alpha OpenAI-Compatible LLM API Proxy",
        description="Production-grade OpenAI-compatible API reverse proxy backed by Ox Alpha.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Middleware registration (executed in reverse order of addition)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RequestContextAndLogMiddleware)

    # CORS configuration
    cors_origins = settings.cors_origins_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if cors_origins else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom Exception Handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        req_id = request_id_ctx.get()
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            error_body = exc.detail
        else:
            error_body = {
                "error": {
                    "message": str(exc.detail),
                    "type": "invalid_request_error" if exc.status_code < 500 else "api_error",
                    "param": None,
                    "code": "http_error",
                }
            }
        headers = dict(exc.headers or {})
        headers["X-Request-ID"] = req_id
        return JSONResponse(status_code=exc.status_code, content=error_body, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        req_id = request_id_ctx.get()
        first_error = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(x) for x in first_error.get("loc", []))
        msg = first_error.get("msg", "Invalid request parameters")

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "message": f"Validation error at '{loc}': {msg}",
                    "type": "invalid_request_error",
                    "param": loc or None,
                    "code": "invalid_request",
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(UpstreamError)
    async def upstream_exception_handler(request: Request, exc: UpstreamError):
        req_id = request_id_ctx.get()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "type": exc.error_type,
                    "param": None,
                    "code": exc.code,
                }
            },
            headers={"X-Request-ID": req_id},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        req_id = request_id_ctx.get()
        logger.exception(f"Unhandled server error for request {req_id}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": "An internal server error occurred while processing the request.",
                    "type": "api_error",
                    "param": None,
                    "code": "internal_error",
                }
            },
            headers={"X-Request-ID": req_id},
        )

    # Register Static Files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Register API routes
    app.include_router(router)

    return app


app = create_app()
