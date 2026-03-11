"""Redis-based sliding window rate limiter."""

import time

import redis

from app.core.config import settings


class RateLimiter:
    def __init__(self):
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """Check if the request is within the rate limit.

        Uses a sliding window algorithm. Checks count BEFORE recording the request.

        Args:
            key: Unique key for the rate limit bucket (e.g. IP address).
            limit: Maximum number of requests allowed in the window.
            window: Time window in seconds.

        Returns:
            True if request is allowed, False if rate limit exceeded.
        """
        now = time.time()
        cutoff = now - window
        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, cutoff)  # remove expired entries
        pipe.zcard(key)  # count BEFORE adding
        pipe.expire(key, window)
        results = pipe.execute()
        count = results[1]
        if count >= limit:
            return False  # over limit — do NOT record this request
        # Under limit: record request
        self._redis.zadd(key, {str(now): now})
        return True

    def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests in the current window.

        Args:
            key: Unique key for the rate limit bucket.
            limit: Maximum number of requests allowed in the window.
            window: Time window in seconds.

        Returns:
            Number of remaining requests allowed.
        """
        now = time.time()
        self._redis.zremrangebyscore(key, 0, now - window)
        count = self._redis.zcard(key)
        return max(0, limit - count)
