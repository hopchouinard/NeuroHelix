"""Rate limiter service for API request throttling."""

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 50  # Conservative limit (below 60/min)
    requests_per_day: int = 1000  # Daily limit
    burst_size: int = 10  # Allow small bursts


class RateLimitError(Exception):
    """Exception raised when rate limit is exceeded."""

    pass


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API requests.

    Uses token bucket algorithm to enforce both per-minute and per-day limits
    while allowing small bursts of requests.
    """

    def __init__(self, config: RateLimitConfig):
        """Initialize the rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config
        self._lock = threading.Lock()

        # Per-minute token bucket
        self._minute_tokens = float(config.burst_size)
        self._minute_last_update = time.time()
        self._minute_capacity = config.burst_size

        # Per-day counter
        self._day_requests = 0
        self._day_reset_time = datetime.now() + timedelta(days=1)

    def _refill_tokens(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._minute_last_update

        # Calculate tokens to add based on rate (requests_per_minute / 60 seconds)
        tokens_per_second = self.config.requests_per_minute / 60.0
        tokens_to_add = elapsed * tokens_per_second

        # Add tokens, capped at capacity
        self._minute_tokens = min(
            self._minute_capacity, self._minute_tokens + tokens_to_add
        )
        self._minute_last_update = now

    def _reset_daily_counter_if_needed(self):
        """Reset daily counter if a day has passed."""
        if datetime.now() >= self._day_reset_time:
            self._day_requests = 0
            self._day_reset_time = datetime.now() + timedelta(days=1)

    def acquire(self, timeout: float = 60.0) -> bool:
        """Acquire permission to make a request.

        Blocks until a token is available or timeout is reached.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if token acquired, False if timeout

        Raises:
            RateLimitError: If daily limit is exceeded
        """
        start_time = time.time()

        while True:
            with self._lock:
                self._refill_tokens()
                self._reset_daily_counter_if_needed()

                # Check daily limit
                if self._day_requests >= self.config.requests_per_day:
                    raise RateLimitError(
                        f"Daily limit of {self.config.requests_per_day} requests exceeded. "
                        f"Resets at {self._day_reset_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )

                # Check if we have tokens available
                if self._minute_tokens >= 1.0:
                    self._minute_tokens -= 1.0
                    self._day_requests += 1
                    return True

            # Check timeout
            if time.time() - start_time >= timeout:
                return False

            # Wait a bit before retrying (adaptive based on token refill rate)
            wait_time = 1.0 / (self.config.requests_per_minute / 60.0)
            time.sleep(min(wait_time, 1.0))

    def try_acquire(self) -> bool:
        """Try to acquire a token without blocking.

        Returns:
            True if token acquired, False otherwise
        """
        with self._lock:
            self._refill_tokens()
            self._reset_daily_counter_if_needed()

            # Check daily limit
            if self._day_requests >= self.config.requests_per_day:
                return False

            # Check if we have tokens available
            if self._minute_tokens >= 1.0:
                self._minute_tokens -= 1.0
                self._day_requests += 1
                return True

            return False

    def get_stats(self) -> dict:
        """Get current rate limiter statistics.

        Returns:
            Dictionary with current stats
        """
        with self._lock:
            self._refill_tokens()
            self._reset_daily_counter_if_needed()

            return {
                "available_tokens": self._minute_tokens,
                "capacity": self._minute_capacity,
                "requests_today": self._day_requests,
                "daily_limit": self.config.requests_per_day,
                "day_resets_at": self._day_reset_time.isoformat(),
                "requests_per_minute": self.config.requests_per_minute,
            }

    def wait_if_needed(self, timeout: float = 60.0) -> None:
        """Wait if necessary to acquire a token.

        Args:
            timeout: Maximum time to wait

        Raises:
            RateLimitError: If timeout or daily limit exceeded
        """
        if not self.acquire(timeout=timeout):
            raise RateLimitError(
                f"Could not acquire rate limit token within {timeout}s timeout"
            )


# Global rate limiter instance (shared across threads)
_global_rate_limiter: TokenBucketRateLimiter | None = None
_rate_limiter_lock = threading.Lock()


def get_rate_limiter(config: RateLimitConfig | None = None) -> TokenBucketRateLimiter:
    """Get or create the global rate limiter instance.

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        Global rate limiter instance
    """
    global _global_rate_limiter

    if _global_rate_limiter is None:
        with _rate_limiter_lock:
            if _global_rate_limiter is None:
                cfg = config or RateLimitConfig()
                _global_rate_limiter = TokenBucketRateLimiter(cfg)

    return _global_rate_limiter


def reset_rate_limiter():
    """Reset the global rate limiter (mainly for testing)."""
    global _global_rate_limiter
    with _rate_limiter_lock:
        _global_rate_limiter = None
