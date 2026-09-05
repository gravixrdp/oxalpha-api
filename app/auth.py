"""API Key Authentication Dependency."""

import secrets
from fastapi import Header, HTTPException, status
from app.config import get_settings


async def verify_api_key(authorization: str | None = Header(default=None)) -> str:
    """Verify incoming Authorization: Bearer <API_KEY> header.

    Uses secrets.compare_digest for constant-time comparison to prevent timing attacks.
    Never logs or leaks the API key in responses.
    """
    settings = get_settings()

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Missing Authorization header. Use 'Authorization: Bearer <API_KEY>'.",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid Authorization format. Expected 'Bearer <API_KEY>'.",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )

    token = parts[1]
    if not secrets.compare_digest(token, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Incorrect API key provided.",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )

    return token
