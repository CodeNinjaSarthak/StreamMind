"""YouTube Live Chat posting worker.

Dequeues posting tasks and posts AI-generated answers to YouTube live chat.
Reads live_chat_id from Redis cache only (set by the polling worker).
"""

import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone

# Ensure project root is on sys.path (for 'workers' package) and
# backend/ is on sys.path (for 'app' package).
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

from app.core.encryption import decrypt_data
from app.db.models.answer import Answer
from app.db.models.cluster import Cluster
from app.db.models.streaming_session import StreamingSession
from app.db.models.youtube_token import YouTubeToken
from app.services.websocket.events import event_service
from app.services.youtube.client import YouTubeClient
from app.services.youtube.quota import YouTubeQuotaService
from workers.common.db import get_db_session
from workers.common.queue import QueueManager, QUEUE_YOUTUBE_POSTING
from workers.common.redis import get_redis_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds
_running = True
_stats = {"posted": 0, "errors": 0, "last_log": time.time()}


def handle_signal(sig, frame):
    global _running
    logger.info("Shutdown signal received, stopping posting worker...")
    _running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def main() -> None:
    """Main posting loop."""
    global _running
    logger.info("Starting YouTube posting worker...")
    manager = QueueManager()
    redis_client = get_redis_client()
    quota_service = YouTubeQuotaService()
    task = None

    while _running:
        try:
            # Log metrics every 60s
            if time.time() - _stats["last_log"] >= 60:
                logger.info(
                    f"Posting stats — posted: {_stats['posted']}, errors: {_stats['errors']}"
                )
                _stats["last_log"] = time.time()

            task = manager.dequeue(QUEUE_YOUTUBE_POSTING)
            if task is None:
                time.sleep(POLL_INTERVAL)
                continue

            answer_id = task.get("answer_id")
            session_id = task.get("session_id")

            for db in get_db_session():
                try:
                    answer = db.query(Answer).filter_by(id=answer_id).first()
                    if not answer:
                        logger.warning(f"Answer {answer_id} not found")
                        break

                    cluster = db.query(Cluster).filter_by(id=answer.cluster_id).first()
                    session = db.query(StreamingSession).filter_by(id=session_id).first()
                    if not session:
                        logger.warning(f"Session {session_id} not found")
                        break

                    token = (
                        db.query(YouTubeToken)
                        .filter_by(teacher_id=session.teacher_id)
                        .first()
                    )
                    if not token:
                        logger.warning(
                            f"No YouTube token for teacher {session.teacher_id}"
                        )
                        break

                    teacher_id_str = str(session.teacher_id)

                    # Check quota before posting
                    if not quota_service.check_quota(teacher_id_str, "post"):
                        logger.warning(
                            f"Daily quota exceeded for posting, teacher {teacher_id_str}"
                        )
                        manager.retry(QUEUE_YOUTUBE_POSTING, task)
                        task = None
                        break

                    # Get live_chat_id from cache only (set by polling worker)
                    live_chat_id = redis_client.get(
                        f"youtube:poll:{session_id}:chat_id"
                    )
                    if not live_chat_id:
                        logger.warning(
                            f"No live_chat_id cached for session {session_id}, retrying"
                        )
                        manager.retry(QUEUE_YOUTUBE_POSTING, task)
                        task = None
                        break

                    access_token = decrypt_data(token.access_token)
                    client = YouTubeClient(access_token)
                    msg_id = client.post_message(live_chat_id, answer.text)
                    quota_service.record_usage(teacher_id_str, "post")

                    answer.is_posted = True
                    answer.posted_at = datetime.now(timezone.utc)
                    answer.youtube_comment_id = msg_id
                    db.commit()
                    _stats["posted"] += 1

                    # Publish event for WebSocket relay
                    event = event_service.create_answer_posted_event(
                        str(answer.id), str(answer.cluster_id)
                    )
                    redis_client.publish(
                        f"ws:{session_id}", json.dumps(event)
                    )
                    logger.info(
                        f"Posted answer {answer_id} to YouTube chat (msg_id={msg_id})"
                    )

                finally:
                    db.close()

            task = None

        except Exception as e:
            _stats["errors"] += 1
            logger.error(f"Posting worker error: {e}", exc_info=True)
            if task:
                manager.retry(QUEUE_YOUTUBE_POSTING, task)
                task = None
            time.sleep(POLL_INTERVAL)

    logger.info("YouTube posting worker shut down gracefully")


if __name__ == "__main__":
    main()
