"""Embeddings worker for generating text embeddings."""

import logging
import os
import sys
import time

# Ensure project root is on sys.path so 'workers' package resolves
# regardless of whether this file is run as a script or as a module.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.common.queue import QueueManager, QUEUE_EMBEDDING

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def main() -> None:
    """Main entry point for embeddings worker."""
    logger.info("Starting embeddings worker...")
    manager = QueueManager()
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_EMBEDDING)
                if task is None:
                    time.sleep(POLL_INTERVAL)
                    continue

                logger.info(
                    "Processing task",
                    extra={
                        "task_id": task.get("task_id"),
                        "comment_id": task.get("comment_id"),
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
                    manager.retry(QUEUE_EMBEDDING, task)
                    task = None
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Embeddings worker shutting down gracefully")


if __name__ == "__main__":
    main()
