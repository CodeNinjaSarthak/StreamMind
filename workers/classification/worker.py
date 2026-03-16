"""Classification worker for processing comments."""

import json
import logging
import os
import sys
import time

# Ensure project root is on sys.path (for 'workers' package) and
# backend/ is on sys.path (for 'app' package).
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

from workers.common.prometheus_setup import setup_multiproc_dir  # noqa: E402

setup_multiproc_dir()

from app.core.config import settings  # noqa: E402
from app.db.models.comment import Comment
from app.services.gemini.client import GeminiClient
from app.services.websocket.events import event_service

from workers.common.db import get_db_session
from workers.common.metrics import (  # noqa: E402
    gemini_circuit_state,
    record_processing,
    update_queue_depths,
)
from workers.common.queue import (
    QUEUE_CLASSIFICATION,
    QUEUE_EMBEDDING,
    QueueManager,
)
from workers.common.redis import get_redis_client
from workers.common.schemas import EmbeddingPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def process_task(task, gemini_client, manager, db, redis_client):
    """Process a single classification task.

    Args:
        task: Dequeued task payload dict.
        gemini_client: GeminiClient instance.
        manager: QueueManager instance.
        db: SQLAlchemy session.
        redis_client: Redis client for event publishing (may be None in tests).
    """
    comment_id = task.get("comment_id")
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        logger.warning(f"Comment {comment_id} not found, skipping")
        return
    result = gemini_client.classify_question(comment.text)
    comment.is_question = result["is_question"]
    comment.confidence_score = result["confidence"]
    if result["is_question"] and result["confidence"] > settings.classification_confidence_threshold:
        manager.enqueue(
            QUEUE_EMBEDDING,
            EmbeddingPayload(comment_id=str(comment.id), text=comment.text).to_dict(),
        )
    elif result["is_question"]:
        logger.warning(
            "Question detected but below confidence threshold",
            extra={
                "comment_id": comment_id,
                "confidence": result["confidence"],
                "threshold": settings.classification_confidence_threshold,
            },
        )

    # Publish event for WebSocket relay
    if redis_client is not None:
        event = event_service.create_comment_classified_event(
            str(comment.id), result["is_question"], result["confidence"]
        )
        redis_client.publish(f"ws:{comment.session_id}", json.dumps(event))

    db.commit()

    logger.info(
        "Classification complete",
        extra={
            "comment_id": comment_id,
            "is_question": result["is_question"],
            "confidence": result["confidence"],
        },
    )


def main() -> None:
    """Main entry point for classification worker."""
    logger.info("Starting classification worker...")
    gemini_client = GeminiClient()
    manager = QueueManager()
    redis_client = get_redis_client()
    task = None

    # Wire circuit breaker state into Prometheus
    _CB_STATE_MAP = {"closed": 0, "half_open": 1, "open": 2}
    gemini_circuit_state.labels(worker_name="classification").set(0)
    gemini_client._circuit_breaker._state_change_callback = lambda state: gemini_circuit_state.labels(
        worker_name="classification"
    ).set(_CB_STATE_MAP.get(state, 0))

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_CLASSIFICATION)
                if task is None:
                    update_queue_depths(manager)
                    time.sleep(POLL_INTERVAL)
                    continue

                proc_start = time.time()
                for db in get_db_session():
                    try:
                        process_task(task, gemini_client, manager, db, redis_client)
                    finally:
                        db.close()
                record_processing("classification", time.time() - proc_start, True)
                task = None

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                if task:
                    record_processing("classification", time.time() - proc_start, False)
                    manager.retry(QUEUE_CLASSIFICATION, task)
                    task = None
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Classification worker shutting down gracefully")


if __name__ == "__main__":
    main()
