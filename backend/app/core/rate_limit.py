"""Rate limiting utilities."""

from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request, status


def rate_limit(
    max_requests: int = 60, window_seconds: int = 60
) -> Callable:
    """Decorator for rate limiting endpoints.

    Args:
        max_requests: Maximum number of requests allowed.
        window_seconds: Time window in seconds.

    Returns:
        Decorator function.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # TODO: Implement actual rate limiting logic with Redis
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

