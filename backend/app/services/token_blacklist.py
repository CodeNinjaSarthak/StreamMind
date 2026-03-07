"""Redis-based JWT token blacklist for logout support."""

import redis

from app.core.config import settings


class TokenBlacklist:
    def __init__(self):
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)

    def blacklist_token(self, token: str, expires_in: int) -> None:
        """Add a token to the blacklist with a TTL matching its remaining lifetime.

        Args:
            token: JWT token string to blacklist.
            expires_in: Seconds until the token expires (TTL for the blacklist entry).
        """
        if expires_in <= 0:
            return  # already expired, no need to blacklist
        key = f"blacklist:token:{token}"
        self._redis.setex(key, expires_in, "1")

    def is_blacklisted(self, token: str) -> bool:
        """Check if a token has been blacklisted.

        Fails closed: if Redis is unavailable, raises the exception so the caller
        treats the token as untrusted rather than letting logged-out tokens through.

        Args:
            token: JWT token string to check.

        Returns:
            True if token is blacklisted, False otherwise.

        Raises:
            redis.RedisError: If Redis is unavailable.
        """
        key = f"blacklist:token:{token}"
        return self._redis.exists(key) == 1


token_blacklist = TokenBlacklist()
