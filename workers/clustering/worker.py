"""Clustering worker for grouping similar comments."""

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
from sklearn.cluster import KMeans
from workers.common.queue import QueueManager, QUEUE_CLUSTERING, QUEUE_ANSWER_GENERATION
from workers.common.db import get_db_session
from workers.common.schemas import AnswerGenerationPayload
from app.db.models.comment import Comment
from app.db.models.cluster import Cluster

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def main() -> None:
    """Main entry point for clustering worker."""
    logger.info("Starting clustering worker...")
    manager = QueueManager()
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_CLUSTERING)
                if task is None:
                    time.sleep(POLL_INTERVAL)
                    continue

                session_id = task.get("session_id")
                comment_ids = task.get("comment_ids", [])

                for db in get_db_session():
                    try:
                        comments = db.query(Comment).filter(
                            Comment.id.in_(comment_ids)
                        ).all()
                        comments = [c for c in comments if c.embedding is not None]
                        if len(comments) < 2:
                            logger.warning(f"Not enough embedded comments ({len(comments)}) to cluster")
                            break

                        embeddings = np.array([c.embedding for c in comments])
                        k = min(max(2, len(comments) // 4), 10)
                        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10).fit(embeddings)

                        payloads = []
                        try:
                            for i in range(k):
                                indices = np.where(kmeans.labels_ == i)[0]
                                if len(indices) == 0:
                                    continue
                                centroid = kmeans.cluster_centers_[i]
                                cluster_embeddings = embeddings[indices]
                                distances = np.linalg.norm(cluster_embeddings - centroid, axis=1)
                                closest_comment = comments[indices[np.argmin(distances)]]
                                cluster = Cluster(
                                    session_id=session_id,
                                    title=closest_comment.text[:200],
                                    centroid_embedding=centroid.tolist(),
                                    comment_count=len(indices),
                                    similarity_threshold=0.8
                                )
                                db.add(cluster)
                                db.flush()
                                cluster_comments = [comments[j] for j in indices]
                                for c in cluster_comments:
                                    c.cluster_id = cluster.id
                                payloads.append(AnswerGenerationPayload(
                                    cluster_id=str(cluster.id),
                                    session_id=session_id,
                                    question_texts=[c.text for c in cluster_comments]
                                ).to_dict())
                            db.commit()
                        except Exception:
                            db.rollback()
                            raise
                        for payload in payloads:
                            manager.enqueue(QUEUE_ANSWER_GENERATION, payload)
                        logger.info(f"Created {k} clusters for session {session_id}")
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
