"""Embeddings worker for generating text embeddings."""

import logging
import os
import sys
import time

# Ensure project root is on sys.path (for 'workers' package) and
# backend/ is on sys.path (for 'app' package).
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

import redis as redis_lib
from workers.common.queue import QueueManager, QUEUE_EMBEDDING, QUEUE_CLUSTERING
from workers.common.db import get_db_session
from workers.common.schemas import ClusteringPayload
from app.services.gemini.client import GeminiClient
from app.db.models.comment import Comment

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def main() -> None:
    """Main entry point for embeddings worker."""
    logger.info("Starting embeddings worker...")
    gemini_client = GeminiClient()
    manager = QueueManager()
    redis_client = redis_lib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    threshold = int(os.getenv("CLUSTERING_THRESHOLD", "5"))
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_EMBEDDING)
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
                        if comment.embedding is not None:
                            logger.info(f"Comment {comment_id} already embedded, skipping")
                            break
                        embedding = gemini_client.generate_embedding(comment.text)
                        comment.embedding = embedding
                        db.commit()
                        # Atomic clustering trigger via Redis INCR
                        count = redis_client.incr(f"question_count:{comment.session_id}")
                        redis_client.expire(f"question_count:{comment.session_id}", 3600)
                        if count == threshold:
                            question_ids = [
                                str(c.id)
                                for c in db.query(Comment)
                                .filter(
                                    Comment.session_id == comment.session_id,
                                    Comment.is_question == True,
                                    Comment.embedding.isnot(None),
                                    Comment.cluster_id.is_(None),
                                )
                                .all()
                            ]
                            manager.enqueue(
                                QUEUE_CLUSTERING,
                                ClusteringPayload(
                                    session_id=str(comment.session_id), comment_ids=question_ids, trigger_type="auto"
                                ).to_dict(),
                            )
                            redis_client.delete(f"question_count:{comment.session_id}")
                        logger.info(f"Embedding stored for comment {comment_id}")
                    finally:
                        db.close()
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
