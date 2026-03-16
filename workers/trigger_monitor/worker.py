# STUB — not wired up. Not started by start_dev.sh. No implementation exists.
"""Trigger monitor worker for monitoring and triggering actions."""

import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for trigger monitor worker."""
    logger.info("Starting trigger monitor worker...")

    # Read environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    logger.info(f"Redis URL: {redis_url}")
    logger.info("Database URL configured")

    logger.info("Trigger monitor worker started successfully")

    # TODO: Implement actual worker logic
    try:
        while True:
            # Worker loop placeholder
            pass
    except KeyboardInterrupt:
        logger.info("Trigger monitor worker shutting down...")


if __name__ == "__main__":
    main()
