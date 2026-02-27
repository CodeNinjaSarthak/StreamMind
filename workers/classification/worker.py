"""Classification worker for processing comments."""

import logging
import os
import sys
import time

# Ensure project root is on sys.path so 'workers' package resolves
# regardless of whether this file is run as a script or as a module.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.common.queue import QueueManager, QUEUE_CLASSIFICATION

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def main() -> None:
    """Main entry point for classification worker."""
    logger.info("Starting classification worker...")
    manager = QueueManager()
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_CLASSIFICATION)
                if task is None:
                    time.sleep(POLL_INTERVAL)
                    continue

                logger.info(
                    "Processing task",
                    extra={
                        "task_id": task.get("task_id"),
                        "comment_id": task.get("comment_id"),
                        "session_id": task.get("session_id"),
                        "text_preview": (task.get("text") or "")[:50],
                    }
                )
                # Phase 1: log-and-ack, no AI processing
                logger.info(
                    "Task acknowledged (no-op — AI logic is Phase 2)",
                    extra={"task_id": task.get("task_id")}
                )
                task = None

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                if task:
                    manager.retry(QUEUE_CLASSIFICATION, task)
                    task = None
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Classification worker shutting down gracefully")


if __name__ == "__main__":
    main()
