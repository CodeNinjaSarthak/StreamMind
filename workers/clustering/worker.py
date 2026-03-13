"""Online nearest-centroid clustering worker."""

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

import numpy as np
from app.db.models.cluster import Cluster
from app.db.models.comment import Comment
from app.services.gemini.client import GeminiClient
from app.services.websocket.events import event_service
from sqlalchemy import text

from workers.common.db import get_db_session
from workers.common.queue import (
    QUEUE_ANSWER_GENERATION,
    QUEUE_CLUSTERING,
    QueueManager,
)
from workers.common.redis import get_redis_client
from workers.common.schemas import AnswerGenerationPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds
SIMILARITY_THRESHOLD = 0.65
ANSWER_GENERATION_MILESTONES = {3, 10, 25}


def main() -> None:
    """Main entry point for clustering worker."""
    logger.info("Starting clustering worker...")
    manager = QueueManager()
    gemini_client = GeminiClient()
    redis_client = get_redis_client()
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_CLUSTERING)
                if task is None:
                    time.sleep(POLL_INTERVAL)
                    continue

                comment_id = task.get("comment_id")
                session_id = task.get("session_id")

                for db in get_db_session():
                    try:
                        comment = db.query(Comment).filter(Comment.id == comment_id).first()
                        if not comment:
                            logger.warning(f"Comment {comment_id} not found, skipping")
                            break
                        if comment.embedding is None:
                            logger.warning(f"Comment {comment_id} has no embedding, skipping")
                            break
                        if not comment.is_question:
                            logger.info(f"Comment {comment_id} is not a question, skipping")
                            break

                        emb_literal = "[" + ",".join(map(str, comment.embedding)) + "]"

                        row = db.execute(
                            text(
                                """
                                SELECT id, centroid_embedding, comment_count,
                                       1 - (centroid_embedding <=> CAST(:emb AS vector)) AS similarity
                                FROM clusters
                                WHERE session_id = :sid
                                ORDER BY centroid_embedding <=> CAST(:emb AS vector)
                                LIMIT 1
                                """
                            ),
                            {"emb": emb_literal, "sid": str(comment.session_id)},
                        ).fetchone()

                        if row is not None and row.similarity >= SIMILARITY_THRESHOLD:
                            # Join existing cluster
                            is_new_cluster = False
                            cluster = db.query(Cluster).filter(Cluster.id == row.id).first()
                            n = cluster.comment_count
                            new_vec = (np.array(cluster.centroid_embedding) * n + np.array(comment.embedding)) / (n + 1)
                            new_vec = new_vec / np.linalg.norm(new_vec)
                            cluster.centroid_embedding = new_vec.tolist()
                            cluster.comment_count = n + 1
                            comment.cluster_id = cluster.id
                            logger.info(
                                f"Comment {comment_id} joined cluster {cluster.id} "
                                f"(similarity={row.similarity:.3f}, count={cluster.comment_count})"
                            )
                        else:
                            # Create new cluster
                            is_new_cluster = True
                            cluster = Cluster(
                                session_id=comment.session_id,
                                title=comment.text[:100] + " [pending]",
                                centroid_embedding=comment.embedding,
                                comment_count=1,
                            )
                            db.add(cluster)
                            db.flush()
                            comment.cluster_id = cluster.id
                            logger.info(f"Created new cluster {cluster.id} for comment {comment_id}")

                        db.commit()
                        db.refresh(cluster)

                        # Publish event for WebSocket relay
                        cluster_data = {
                            "id": str(cluster.id),
                            "title": cluster.title,
                            "comment_count": cluster.comment_count,
                        }
                        if is_new_cluster:
                            event = event_service.create_cluster_created_event(cluster_data)
                        else:
                            event = event_service.create_cluster_updated_event(cluster_data)
                        redis_client.publish(
                            f"ws:{comment.session_id}", json.dumps(event)
                        )

                        cluster_comments = (
                            db.query(Comment)
                            .filter(
                                Comment.cluster_id == cluster.id,
                                Comment.is_question.is_(True),
                            )
                            .all()
                        )

                        # Summarize at 3 comments
                        if cluster.comment_count == 3:
                            try:
                                summary = gemini_client.summarize_cluster([c.text for c in cluster_comments])
                                cluster.title = summary
                                db.commit()
                                logger.info(f"Cluster {cluster.id} title updated: {summary!r}")
                            except Exception as e:
                                logger.error(f"Failed to summarize cluster {cluster.id}: {e}")

                        # Enqueue answer generation on new cluster or milestones
                        if is_new_cluster or cluster.comment_count in ANSWER_GENERATION_MILESTONES:
                            manager.enqueue(
                                QUEUE_ANSWER_GENERATION,
                                AnswerGenerationPayload(
                                    cluster_id=str(cluster.id),
                                    session_id=str(comment.session_id),
                                    question_texts=[c.text for c in cluster_comments],
                                ).to_dict(),
                            )
                            logger.info(
                                f"Enqueued answer generation for cluster {cluster.id} "
                                f"(new={is_new_cluster}, count={cluster.comment_count})"
                            )

                    finally:
                        db.close()
                task = None

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                if task:
                    manager.retry(QUEUE_CLUSTERING, task)
                    task = None
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Clustering worker shutting down gracefully")


if __name__ == "__main__":
    main()
