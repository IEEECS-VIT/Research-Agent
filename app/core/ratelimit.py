import time
from collections import defaultdict
from fastapi import Request, HTTPException


class InMemoryRateLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self.window_seconds

        timestamps = self._requests[client_ip]
        timestamps[:] = [t for t in timestamps if t > window_start]

        if len(timestamps) >= self.max_requests:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later.",
            )

        timestamps.append(now)


rate_limiter = InMemoryRateLimiter()
