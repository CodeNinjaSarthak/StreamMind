"""Answer generation worker for creating AI answers."""

import logging
import os
import sys
import time

# Ensure project root is on sys.path (for 'workers' package) and
# backend/ is on sys.path (for 'app' package).
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

from sqlalchemy import text
from workers.common.queue import QueueManager, QUEUE_ANSWER_GENERATION, QUEUE_YOUTUBE_POSTING
from workers.common.db import get_db_session
from workers.common.schemas import YouTubePostingPayload
from app.services.gemini.client import GeminiClient, vector_to_literal
from app.db.models.cluster import Cluster
from app.db.models.answer import Answer
from app.db.models.streaming_session import StreamingSession
from app.db.models.youtube_token import YouTubeToken

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds


def main() -> None:
    """Main entry point for answer generation worker."""
    logger.info("Starting answer generation worker...")
    gemini_client = GeminiClient()
    manager = QueueManager()
    task = None

    try:
        while True:
            try:
                task = manager.dequeue(QUEUE_ANSWER_GENERATION)
                if task is None:
                    time.sleep(POLL_INTERVAL)
                    continue

                cluster_id = task.get("cluster_id")
                question_texts = task.get("question_texts", [])

                for db in get_db_session():
                    try:
                        cluster = db.query(Cluster).filter(Cluster.id == cluster_id).first()
                        if not cluster:
                            logger.warning(f"Cluster {cluster_id} not found, skipping")
                            break

                        # RAG retrieval via pgvector cosine distance
                        rows = db.execute(
                            text(
                                "SELECT content FROM rag_documents "
                                "ORDER BY embedding <-> CAST(:centroid AS vector) LIMIT 5"
                            ),
                            {"centroid": vector_to_literal(cluster.centroid_embedding)},
                        ).fetchall()
                        context = "\n\n".join(r.content for r in rows) if rows else None

                        questions_text = "\n".join(f"- {q}" for q in question_texts)
                        if context:
                            logger.debug("RAG context found, using %d chunks for cluster %s", len(rows), cluster_id)
                        else:
                            logger.info("No RAG context for cluster %s — using general knowledge fallback", cluster_id)
                        answer_text = gemini_client.generate_answer(questions_text, context)

                        answer = Answer(cluster_id=cluster.id, text=answer_text, is_posted=False)
                        db.add(answer)
                        db.commit()
                        logger.info(f"Answer generated for cluster {cluster_id}, answer_id={answer.id}")

                        # Auto-enqueue to YouTube posting if session has YouTube connected
                        session = db.query(StreamingSession).filter(StreamingSession.id == cluster.session_id).first()
                        if session and session.youtube_video_id:
                            yt_token = (
                                db.query(YouTubeToken).filter(YouTubeToken.teacher_id == session.teacher_id).first()
                            )
                            if yt_token:
                                manager.enqueue(
                                    QUEUE_YOUTUBE_POSTING,
                                    YouTubePostingPayload(
                                        answer_id=str(answer.id), session_id=str(session.id)
                                    ).to_dict(),
                                )
                                logger.info(f"Enqueued answer {answer.id} for YouTube posting")
                    finally:
                        db.close()
                task = None

            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                if task:
                    manager.retry(QUEUE_ANSWER_GENERATION, task)
                    task = None
                time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Answer generation worker shutting down gracefully")


if __name__ == "__main__":
    main()
