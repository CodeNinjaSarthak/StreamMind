"""Structured logging configuration."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: Log record to format.

        Returns:
            JSON formatted log string.
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if hasattr(record, "teacher_id"):
            log_data["teacher_id"] = record.teacher_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StandardFormatter(logging.Formatter):
    """Standard text log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as text.

        Args:
            record: Log record to format.

        Returns:
            Formatted log string.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        base_msg = f"{timestamp} - {record.levelname} - {record.name} - {record.getMessage()}"

        if hasattr(record, "request_id"):
            base_msg = f"[{record.request_id}] {base_msg}"

        return base_msg


def setup_logging() -> None:
    """Configure application logging."""
    log_level = getattr(logging, settings.log_level.upper())

    if settings.log_json:
        formatter = JSONFormatter()
    else:
        formatter = StandardFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers = []
    root_logger.addHandler(handler)

    logging.getLogger("uvicorn").setLevel(log_level)
    logging.getLogger("fastapi").setLevel(log_level)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with structured logging support.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for adding contextual information."""

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Process log message with extra context.

        Args:
            msg: Log message.
            kwargs: Keyword arguments.

        Returns:
            Processed message and kwargs.
        """
        extra = kwargs.get("extra", {})
        if self.extra:
            extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def get_context_logger(name: str, **context: Any) -> LoggerAdapter:
    """Get logger with contextual information.

    Args:
        name: Logger name.
        **context: Context key-value pairs.

    Returns:
        Logger adapter with context.
    """
    logger = get_logger(name)
    return LoggerAdapter(logger, context)
