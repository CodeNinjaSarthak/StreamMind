"""Rate limiting utilities."""

from functools import wraps
from typing import Callable

from fastapi import HTTPException, Request, status

from app.services.rate_limiter import RateLimiter

_rate_limiter = RateLimiter()


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
            client_ip = request.client.host if request.client else "unknown"
            key = f"rate_limit:{func.__module__}.{func.__name__}:{client_ip}"
            allowed = _rate_limiter.check_rate_limit(key, max_requests, window_seconds)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please try again later.",
                )
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

