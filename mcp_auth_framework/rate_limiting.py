"""Rate limiting utilities for OAuth endpoints."""

import time
from collections import defaultdict


class SlidingWindowRateLimiter:
    """Simple in-memory rate limiter for OAuth endpoints.

    Tracks requests per client within a sliding time window.
    Thread-safe for async usage within a single process.
    """

    def __init__(self, requests_per_window: int, window_seconds: int):
        """Initialize the rate limiter.

        Args:
            requests_per_window: Maximum number of requests allowed in the window
            window_seconds: Size of the time window in seconds
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self.clients: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if the client is allowed to make a request.

        Args:
            client_id: OAuth client identifier

        Returns:
            True if the request is allowed, False if rate limited
        """
        now = time.time()
        # Clean old requests outside the window
        self.clients[client_id] = [
            req_time for req_time in self.clients[client_id] if now - req_time < self.window_seconds
        ]

        if len(self.clients[client_id]) >= self.requests_per_window:
            return False

        self.clients[client_id].append(now)
        return True

    def get_retry_after(self, client_id: str) -> int:
        """Get the number of seconds until the client can retry.

        Args:
            client_id: OAuth client identifier

        Returns:
            Number of seconds to wait before retrying (minimum 1)
        """
        if not self.clients[client_id]:
            return 0
        oldest_request = min(self.clients[client_id])
        retry_after = int(self.window_seconds - (time.time() - oldest_request)) + 1
        return max(retry_after, 1)
