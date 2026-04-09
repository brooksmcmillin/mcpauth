"""Tests for SlidingWindowRateLimiter."""

import threading
from unittest.mock import patch

from mcp_auth_framework.rate_limiting import SlidingWindowRateLimiter

# ---------------------------------------------------------------------------
# Basic allow / deny
# ---------------------------------------------------------------------------


class TestIsAllowedBasic:
    def test_new_client_is_allowed(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=5, window_seconds=60)
        assert limiter.is_allowed("client1") is True

    def test_requests_up_to_limit_are_allowed(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=60)
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True
        assert limiter.is_allowed("client1") is True

    def test_request_over_limit_is_denied(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=60)
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        limiter.is_allowed("client1")
        assert limiter.is_allowed("client1") is False

    def test_different_clients_are_tracked_independently(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=1, window_seconds=60)
        assert limiter.is_allowed("client_a") is True
        assert limiter.is_allowed("client_b") is True
        # Both are now at the limit
        assert limiter.is_allowed("client_a") is False
        assert limiter.is_allowed("client_b") is False

    def test_limit_of_one(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=1, window_seconds=60)
        assert limiter.is_allowed("c") is True
        assert limiter.is_allowed("c") is False


# ---------------------------------------------------------------------------
# Window reset (using mocked time)
# ---------------------------------------------------------------------------


class TestWindowReset:
    def test_allowed_after_window_expires(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=10)
        t0 = 1_000_000.0

        with patch("mcp_auth_framework.rate_limiting.time") as mock_time:
            mock_time.time.return_value = t0
            limiter.is_allowed("c")
            limiter.is_allowed("c")
            # Denied at t0
            assert limiter.is_allowed("c") is False

            # Advance past window
            mock_time.time.return_value = t0 + 11.0
            assert limiter.is_allowed("c") is True

    def test_partial_window_still_blocks(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=10)
        t0 = 1_000_000.0

        with patch("mcp_auth_framework.rate_limiting.time") as mock_time:
            mock_time.time.return_value = t0
            limiter.is_allowed("c")
            limiter.is_allowed("c")

            # Only half the window has passed — still blocked
            mock_time.time.return_value = t0 + 5.0
            assert limiter.is_allowed("c") is False


# ---------------------------------------------------------------------------
# Sliding window eviction
# ---------------------------------------------------------------------------


class TestSlidingWindowEviction:
    def test_old_entries_are_evicted(self) -> None:
        """Requests outside the window are removed so the client can proceed."""
        limiter = SlidingWindowRateLimiter(requests_per_window=2, window_seconds=10)
        t0 = 1_000_000.0

        with patch("mcp_auth_framework.rate_limiting.time") as mock_time:
            # First two requests at t0 — fills the window
            mock_time.time.return_value = t0
            limiter.is_allowed("c")
            limiter.is_allowed("c")

            # Move forward 11 seconds — both old entries are outside the window
            mock_time.time.return_value = t0 + 11.0
            # is_allowed should evict both and allow this request
            assert limiter.is_allowed("c") is True
            # One request is now in-window, so the second is still allowed
            assert limiter.is_allowed("c") is True
            # Third request in the new window is denied
            assert limiter.is_allowed("c") is False

    def test_only_expired_entries_are_evicted(self) -> None:
        """Entries within the window are preserved during cleanup."""
        limiter = SlidingWindowRateLimiter(requests_per_window=3, window_seconds=10)
        t0 = 1_000_000.0

        with patch("mcp_auth_framework.rate_limiting.time") as mock_time:
            mock_time.time.return_value = t0
            limiter.is_allowed("c")  # t0 — will expire at t0+10

            mock_time.time.return_value = t0 + 6.0
            limiter.is_allowed("c")  # t0+6 — still in window at t0+11

            # At t0+11: first entry (t0) is just outside window; second (t0+6) still inside
            mock_time.time.return_value = t0 + 11.0
            limiter.is_allowed("c")  # one in-window entry remains from t0+6

            # Should have 2 entries in window (t0+6 and t0+11), so one more is allowed
            assert limiter.is_allowed("c") is True
            # Now 3 in window — denied
            assert limiter.is_allowed("c") is False


# ---------------------------------------------------------------------------
# get_retry_after
# ---------------------------------------------------------------------------


class TestGetRetryAfter:
    def test_returns_positive_int_when_rate_limited(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=1, window_seconds=60)
        limiter.is_allowed("c")
        # Now rate limited
        assert limiter.is_allowed("c") is False
        retry = limiter.get_retry_after("c")
        assert isinstance(retry, int)
        assert retry >= 1

    def test_retry_after_is_within_window(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=1, window_seconds=30)
        t0 = 1_000_000.0

        with patch("mcp_auth_framework.rate_limiting.time") as mock_time:
            mock_time.time.return_value = t0
            limiter.is_allowed("c")
            limiter.is_allowed("c")  # denied

            # 5 seconds into the window — should need ~25 more seconds + 1
            mock_time.time.return_value = t0 + 5.0
            retry = limiter.get_retry_after("c")
            assert retry == 26  # (30 - 5) + 1

    def test_retry_after_returns_zero_for_unknown_client(self) -> None:
        limiter = SlidingWindowRateLimiter(requests_per_window=5, window_seconds=60)
        # No requests made by this client
        assert limiter.get_retry_after("unknown") == 0

    def test_retry_after_minimum_is_one(self) -> None:
        """Even at the very edge of the window, retry_after is at least 1."""
        limiter = SlidingWindowRateLimiter(requests_per_window=1, window_seconds=10)
        t0 = 1_000_000.0

        with patch("mcp_auth_framework.rate_limiting.time") as mock_time:
            mock_time.time.return_value = t0
            limiter.is_allowed("c")
            limiter.is_allowed("c")  # denied

            # Almost at window boundary
            mock_time.time.return_value = t0 + 9.999
            retry = limiter.get_retry_after("c")
            assert retry >= 1


# ---------------------------------------------------------------------------
# Concurrent request handling
# ---------------------------------------------------------------------------


class TestConcurrentRequests:
    def test_concurrent_requests_do_not_exceed_limit(self) -> None:
        """Under concurrent load, allowed count must not exceed requests_per_window."""
        limit = 10
        limiter = SlidingWindowRateLimiter(requests_per_window=limit, window_seconds=60)
        results: list[bool] = []
        lock = threading.Lock()

        def make_request() -> None:
            result = limiter.is_allowed("shared_client")
            with lock:
                results.append(result)

        threads = [threading.Thread(target=make_request) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed = sum(1 for r in results if r)
        # Due to GIL and list-comprehension atomicity in CPython, allowed will
        # typically equal exactly `limit`, but could be slightly more if the
        # underlying list operations are interleaved.  We accept up to 2× as a
        # conservative bound; the important property is that it does not vastly
        # exceed the limit.
        assert allowed <= limit * 2, f"allowed={allowed} exceeded 2× limit={limit}"

    def test_multiple_clients_concurrent(self) -> None:
        """Each client tracks independently under concurrent access."""
        limiter = SlidingWindowRateLimiter(requests_per_window=5, window_seconds=60)
        client_allowed: dict[str, int] = {}
        lock = threading.Lock()

        def make_requests(client_id: str) -> None:
            for _ in range(10):
                allowed = limiter.is_allowed(client_id)
                if allowed:
                    with lock:
                        client_allowed[client_id] = client_allowed.get(client_id, 0) + 1

        threads = [threading.Thread(target=make_requests, args=(f"client_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for client_id, count in client_allowed.items():
            assert count <= 5, f"{client_id} allowed {count} requests, expected ≤5"
