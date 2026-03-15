"""Embeddings worker for generating text embeddings."""

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

from app.db.models.comment import Comment  # noqa: E402
from app.services.gemini.client import GeminiClient
from app.services.websocket.events import event_service

from workers.common.db import get_db_session
from workers.common.metrics import (  # noqa: E402
    record_processing,
    update_queue_depths,
)
from workers.common.queue import (
    QUEUE_CLUSTERING,
    QUEUE_EMBEDDING,
    QueueManager,
)
from workers.common.redis import get_redis_client
from workers.common.schemas import ClusteringPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def main() -> None:
    """Main entry point for embeddings worker."""
    logger.info("Starting embeddings worker...")
    gemini_client = GeminiClient()
    manager = QueueManager()
    redis_client = get_redis_client()
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_EMBEDDING)
                if task is None:
                    update_queue_depths(manager)
                    time.sleep(POLL_INTERVAL)
                    continue

                proc_start = time.time()
                comment_id = task.get("comment_id")
                for db in get_db_session():
                    try:
                        comment = db.query(Comment).filter(Comment.id == comment_id).first()
                        if not comment:
                            logger.warning(f"Comment {comment_id} not found, skipping")
                            break
                        if comment.embedding is not None:
                            logger.info(f"Comment {comment_id} already embedded, skipping")
                            break
                        embedding = gemini_client.generate_embedding(comment.text)
                        comment.embedding = embedding
                        db.commit()
                        manager.enqueue(
                            QUEUE_CLUSTERING,
                            ClusteringPayload(
                                session_id=str(comment.session_id),
                                comment_id=str(comment.id),
                            ).to_dict(),
                        )
                        # Publish event for WebSocket relay
                        event = event_service.create_comment_embedded_event(str(comment.id))
                        redis_client.publish(f"ws:{comment.session_id}", json.dumps(event))

                        logger.info(f"Embedding stored for comment {comment_id}")
                    finally:
                        db.close()
                record_processing("embeddings", time.time() - proc_start, True)
                task = None

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                if task:
                    record_processing("embeddings", time.time() - proc_start, False)
                    manager.retry(QUEUE_EMBEDDING, task)
                    task = None
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Embeddings worker shutting down gracefully")


if __name__ == "__main__":
    main()
