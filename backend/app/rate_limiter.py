import logging
import os
import time
from collections import defaultdict, deque
from typing import Dict
from fastapi import HTTPException, Request, status

import app.config  # Ensures .env / tmdb.env are loaded

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    KISS Sliding-Window In-Memory Rate Limiter.
    Enforces a maximum number of requests per window (default 60 seconds) per client IP.
    Single Responsibility: Rate limiting client requests and returning 429 when exceeded.
    """

    def __init__(self, requests_per_window: int = 15, window_seconds: int = 60, name: str = "default"):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.name = name
        self._history: Dict[str, deque] = defaultdict(deque)
        self._last_prune = time.time()

    def _get_client_ip(self, request: Request) -> str:
        """Extracts the client IP from X-Forwarded-For (if proxied) or direct client host."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # First IP in the comma-separated list is the original client
            ip = forwarded.split(",")[0].strip()
            if ip:
                return ip
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def _prune_stale_entries(self, now: float) -> None:
        """Periodically cleans up old client IP records to keep memory bounded."""
        if now - self._last_prune < self.window_seconds:
            return
        self._last_prune = now
        stale_ips = [
            ip for ip, queue in self._history.items()
            if not queue or queue[-1] < (now - self.window_seconds)
        ]
        for ip in stale_ips:
            del self._history[ip]

    def reset(self) -> None:
        """Clears all rate-limiting state (useful for unit tests)."""
        self._history.clear()
        self._last_prune = time.time()

    async def __call__(self, request: Request) -> None:
        """
        FastAPI dependency handler.
        Raises HTTP 429 Too Many Requests if client exceeded allowed requests.
        """
        # Allow disabling rate limiting via env var (e.g. for development or testing)
        if os.getenv("DISABLE_RATE_LIMITER", "").lower() in ("true", "1", "yes"):
            return

        now = time.time()
        self._prune_stale_entries(now)

        ip = self._get_client_ip(request)
        queue = self._history[ip]

        # Evict timestamps older than the sliding window
        threshold = now - self.window_seconds
        while queue and queue[0] <= threshold:
            queue.popleft()

        # Check limit
        if len(queue) >= self.requests_per_window:
            retry_after = max(1, int(queue[0] + self.window_seconds - now))
            logger.warning(
                f"Rate limit exceeded on '{self.name}' for IP {ip}: "
                f"{len(queue)}/{self.requests_per_window} reqs. Retry after {retry_after}s."
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Zu viele Anfragen. Bitte versuche es in {retry_after} Sekunden erneut.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        # Record this request
        queue.append(now)


# Preconfigured rate limiter instances
# General API limiter: 60 requests/minute
general_rate_limiter = RateLimiter(
    requests_per_window=int(os.getenv("RATE_LIMIT_GENERAL_PER_MINUTE", "60")),
    window_seconds=60,
    name="general",
)

# Match endpoint limiter (expensive scraping workload): 15 requests/minute
match_rate_limiter = RateLimiter(
    requests_per_window=int(os.getenv("RATE_LIMIT_MATCH_PER_MINUTE", "15")),
    window_seconds=60,
    name="match",
)
