"""Classification worker for processing comments."""

import logging
import os
import sys
import time

# Ensure project root is on sys.path (for 'workers' package) and
# backend/ is on sys.path (for 'app' package).
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

import json
from workers.common.queue import QueueManager, QUEUE_CLASSIFICATION, QUEUE_EMBEDDING
from workers.common.db import get_db_session
from workers.common.schemas import EmbeddingPayload
from app.services.gemini.client import GeminiClient
from app.db.models.comment import Comment

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def main() -> None:
    """Main entry point for classification worker."""
    logger.info("Starting classification worker...")
    gemini_client = GeminiClient()
    manager = QueueManager()
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_CLASSIFICATION)
                if task is None:
                    time.sleep(POLL_INTERVAL)
                    continue

                comment_id = task.get("comment_id")
                for db in get_db_session():
                    try:
                        comment = db.query(Comment).filter(Comment.id == comment_id).first()
                        if not comment:
                            logger.warning(f"Comment {comment_id} not found, skipping")
                            break
                        result = gemini_client.classify_question(comment.text)
                        comment.is_question = result["is_question"]
                        comment.confidence_score = result["confidence"]
                        db.commit()
                        if result["is_question"]:
                            manager.enqueue(
                                QUEUE_EMBEDDING,
                                EmbeddingPayload(comment_id=str(comment.id), text=comment.text).to_dict(),
                            )
                        logger.info(
                            "Classification complete",
                            extra={
                                "comment_id": comment_id,
                                "is_question": result["is_question"],
                                "confidence": result["confidence"],
                            },
                        )
                    finally:
                        db.close()
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
