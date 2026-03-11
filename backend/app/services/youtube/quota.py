"""YouTube API quota management service (Redis-backed)."""

import redis as redis_lib
from datetime import date, datetime, timedelta, timezone

from app.core.config import settings

QUOTA_COSTS = {"poll": 5, "post": 50, "get_chat_id": 1}
DAILY_LIMIT = 10000


class YouTubeQuotaService:
    """Service for managing YouTube API quota usage."""

    def __init__(self):
        self._redis = redis_lib.from_url(settings.redis_url, decode_responses=True)

    def _key(self, teacher_id: str) -> str:
        return f"yt_quota:{teacher_id}:{date.today().isoformat()}"

    def _ttl_to_midnight(self) -> int:
        """Seconds until next UTC midnight (quota reset time)."""
        now = datetime.now(timezone.utc)
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return max(1, int((midnight - now).total_seconds()))

    def check_quota(self, teacher_id: str, operation: str) -> bool:
        """Check if quota allows an operation.

        Args:
            teacher_id: Teacher ID string.
            operation: Operation type ('poll', 'post', 'get_chat_id').

        Returns:
            True if quota allows, False if limit would be exceeded.
        """
        used = int(self._redis.get(self._key(teacher_id)) or 0)
        return (used + QUOTA_COSTS.get(operation, 0)) <= DAILY_LIMIT

    def record_usage(self, teacher_id: str, operation: str) -> None:
        """Record quota usage for an operation.

        Args:
            teacher_id: Teacher ID string.
            operation: Operation type.
        """
        cost = QUOTA_COSTS.get(operation, 0)
        key = self._key(teacher_id)
        pipe = self._redis.pipeline()
        pipe.incrby(key, cost)
        pipe.expire(key, self._ttl_to_midnight())
        pipe.execute()

    def get_usage(self, teacher_id: str) -> int:
        """Get current quota usage for a teacher.

        Args:
            teacher_id: Teacher ID string.

        Returns:
            Current quota used today.
        """
        return int(self._redis.get(self._key(teacher_id)) or 0)
