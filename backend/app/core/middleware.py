"""Request middleware for context tracking and observability."""

import time
import uuid
from contextvars import ContextVar
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.core.logging import get_logger

logger = get_logger(__name__)

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
teacher_id_var: ContextVar[Optional[str]] = ContextVar("teacher_id", default=None)


def get_request_id() -> Optional[str]:
    """Get current request ID from context.

    Returns:
        Current request ID or None.
    """
    return request_id_var.get()


def get_teacher_id() -> Optional[str]:
    """Get current teacher ID from context.

    Returns:
        Current teacher ID or None.
    """
    return teacher_id_var.get()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking request context and metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track context.

        Args:
            request: Incoming request.
            call_next: Next middleware/handler.

        Returns:
            Response from handler.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)

        start_time = time.time()

        try:
            response = await call_next(request)

            process_time = time.time() - start_time

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)

            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                }
            )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                }
            )
            raise

        finally:
            request_id_var.set(None)
            teacher_id_var.set(None)
