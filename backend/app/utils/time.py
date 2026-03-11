"""Time utility functions."""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Get current UTC datetime.

    Returns:
        Current UTC datetime.
    """
    return datetime.now(timezone.utc)


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string to datetime object.

    Args:
        dt_str: Datetime string.

    Returns:
        Datetime object or None if parsing fails.
    """
    # TODO: Implement actual datetime parsing
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None
