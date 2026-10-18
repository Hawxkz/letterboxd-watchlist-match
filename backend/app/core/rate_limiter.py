import logging
import os
import time
from collections import defaultdict, deque
from typing import Dict
from fastapi import HTTPException, Request, status
import app.core.config  # Ensures .env is loaded

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Limits the number of requests per sliding time window (default 60s) per client IP.
    Single Responsibility: Endpoint protection against overload and spamming.
    """

    def __init__(self, requests_per_window: int = 15, window_seconds: int = 60, name: str = "default"):
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.name = name
        self._history: Dict[str, deque] = defaultdict(deque)
        self._last_prune = time.time()

    def _get_client_ip(self, request: Request) -> str:
        """
        Extracts the client IP, preferring X-Forwarded-For, then X-Real-IP, then the ASGI client host.
        This covers common deployment scenarios (reverse proxy setting X-Forwarded-For)
        while falling back to request.client.host when present. As a last resort
        returns the loopback address to keep the logic deterministic for tests.
        """
        # Prefer X-Forwarded-For when provided by a trusted reverse proxy
        forwarded = request.headers.get("X-Forwarded-For") or request.headers.get("x-forwarded-for")
        if forwarded:
            # First IP in the comma-separated list is the original client
            ip = forwarded.split(",")[0].strip()
            if ip:
                return ip

        # Some proxies use X-Real-IP
        real_ip = request.headers.get("X-Real-IP") or request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()

        # Fall back to the ASGI client host if available
        try:
            client = getattr(request, "client", None)
            if client and getattr(client, "host", None):
                return client.host
        except Exception:
            pass

        # Default deterministic fallback used in tests / unusual environments
        return "127.0.0.1"

    def _prune_stale_entries(self, now: float) -> None:
        """Periodically removes stale client IP records to keep memory bounded."""
        if now - self._last_prune < self.window_seconds:
            return
        self._last_prune = now
        to_delete = [
            ip for ip, q in self._history.items()
            if not q or (now - q[-1] > self.window_seconds * 2)
        ]
        for ip in to_delete:
            del self._history[ip]

    def reset(self) -> None:
        """Resets the internal tracking history (useful for unit tests)."""
        self._history.clear()
        self._last_prune = time.time()

    async def __call__(self, request: Request) -> None:
        """FastAPI dependency handler: Enforces limits and raises HTTP 429 when exceeded."""
        if os.getenv("DISABLE_RATE_LIMITER", "").lower() in ("true", "1", "yes"):
            return

        now = time.time()
        self._prune_stale_entries(now)

        ip = self._get_client_ip(request)
        queue = self._history[ip]

        # Evict timestamps older than the sliding window threshold
        threshold = now - self.window_seconds
        while queue and queue[0] <= threshold:
            queue.popleft()

        # Check rate limit
        if len(queue) >= self.requests_per_window:
            retry_after = max(1, int(queue[0] + self.window_seconds - now))
            logger.warning(
                f"Rate limit exceeded on '{self.name}' for IP {ip}: "
                f"{len(queue)}/{self.requests_per_window}. Retry after {retry_after}s."
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Please retry after {retry_after} seconds.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.requests_per_window),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                },
            )

        # Record this request timestamp
        queue.append(now)


# 1. General API limit (e.g. root, health checks): 60 requests / minute
general_rate_limiter = RateLimiter(
    requests_per_window=int(os.getenv("RATE_LIMIT_GENERAL_PER_MINUTE", "60")),
    window_seconds=60,
    name="general",
)

# 2. Match endpoint limiter (expensive scraping workload): 15 requests / minute
match_rate_limiter = RateLimiter(
    requests_per_window=int(os.getenv("RATE_LIMIT_MATCH_PER_MINUTE", "15")),
    window_seconds=60,
    name="match",
)
