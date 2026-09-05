"""Thread-safe in-memory sliding window rate limiter."""

import asyncio
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status
from app.config import get_settings


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding window rate limiter."""

    def __init__(self, requests_limit: int, window_seconds: int) -> None:
        self.requests_limit = requests_limit
        self.window_seconds = window_seconds
        self._records: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.monotonic()

    async def check(self, key: str) -> None:
        """Check if request exceeds rate limit. Raises 429 if exceeded."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        async with self._lock:
            # Periodic cleanup of keys with empty or completely expired queues
            if now - self._last_cleanup > self.window_seconds:
                self._cleanup(cutoff)
                self._last_cleanup = now

            timestamps = self._records[key]

            # Remove timestamps outside the sliding window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.requests_limit:
                earliest = timestamps[0]
                retry_after = max(1, int(earliest + self.window_seconds - now) + 1)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": {
                            "message": f"Rate limit exceeded. Limit is {self.requests_limit} requests per {self.window_seconds}s. Try again in {retry_after} seconds.",
                            "type": "rate_limit_error",
                            "param": None,
                            "code": "rate_limit_exceeded",
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)

    def _cleanup(self, cutoff: float) -> None:
        """Remove empty or completely expired client keys."""
        to_delete = []
        for k, timestamps in self._records.items():
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()
            if not timestamps:
                to_delete.append(k)
        for k in to_delete:
            del self._records[k]


_rate_limiter: SlidingWindowRateLimiter | None = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Retrieve or initialize the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        _rate_limiter = SlidingWindowRateLimiter(
            requests_limit=settings.RATE_LIMIT_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW,
        )
    return _rate_limiter


async def check_rate_limit(request: Request) -> None:
    """FastAPI dependency to enforce rate limit per client IP."""
    limiter = get_rate_limiter()
    # Use client IP or fallback to header if behind proxy
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    elif request.client and request.client.host:
        client_ip = request.client.host
    else:
        client_ip = "127.0.0.1"

    await limiter.check(client_ip)
