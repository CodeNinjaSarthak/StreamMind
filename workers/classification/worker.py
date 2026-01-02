"""Classification worker for processing comments."""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main entry point for classification worker."""
    logger.info("Starting classification worker...")
    
    # Read environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    database_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/dbname")
    
    logger.info(f"Redis URL: {redis_url}")
    logger.info(f"Database URL configured")
    
    logger.info("Classification worker started successfully")
    
    # TODO: Implement actual worker logic
    try:
        while True:
            # Worker loop placeholder
            pass
    except KeyboardInterrupt:
        logger.info("Classification worker shutting down...")


if __name__ == "__main__":
    main()

