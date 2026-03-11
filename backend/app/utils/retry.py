"""Retry utility functions."""

import asyncio
from typing import Callable, TypeVar, Any
from functools import wraps

T = TypeVar("T")


async def retry_async(
    func: Callable[..., Any],
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    *args,
    **kwargs,
) -> Any:
    """Retry an async function with exponential backoff.

    Args:
        func: Async function to retry.
        max_attempts: Maximum number of retry attempts.
        delay: Initial delay in seconds.
        backoff: Backoff multiplier.
        *args: Positional arguments for func.
        **kwargs: Keyword arguments for func.

    Returns:
        Result of the function call.

    Raises:
        Exception: If all retry attempts fail.
    """
    last_exception = None
    current_delay = delay

    for attempt in range(max_attempts):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_attempts - 1:
                await asyncio.sleep(current_delay)
                current_delay *= backoff

    raise last_exception
