"""Monitoring background task."""

from backend.app.core.logging import get_logger

logger = get_logger(__name__)


async def collect_metrics() -> None:
    """Collect system metrics.

    This task should run periodically to collect and report metrics.
    """
    logger.info("Starting metrics collection")
    # TODO: Implement actual metrics collection
    logger.info("Metrics collection completed")


async def schedule_monitoring() -> None:
    """Schedule monitoring tasks."""
    # TODO: Implement scheduling logic
    pass

