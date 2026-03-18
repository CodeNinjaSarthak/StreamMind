"""Mock YouTube polling worker for local development.

Generates synthetic student comments and feeds them into the DB + queue pipeline,
enabling end-to-end testing of classification, embedding, clustering, and answer
generation workers without any YouTube API dependency.
"""

import json
import logging
import os
import random
import signal
import sys
import time
from datetime import (
    datetime,
    timezone,
)
from uuid import uuid4

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

from app.core.config import settings  # noqa: E402
from app.db.models.comment import Comment  # noqa: E402
from app.db.models.streaming_session import StreamingSession  # noqa: E402
from app.services.websocket.events import event_service  # noqa: E402

from workers.common.db import get_db_session  # noqa: E402
from workers.common.queue import (  # noqa: E402
    QUEUE_CLASSIFICATION,
    QueueManager,
)
from workers.common.redis import get_redis_client  # noqa: E402
from workers.common.schemas import ClassificationPayload  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_running = True
_stats = {"cycles": 0, "messages": 0, "errors": 0, "last_log": time.time()}

# ---------------------------------------------------------------------------
# Themed message corpus
# ---------------------------------------------------------------------------

CLUSTERS = {
    "python_basics": [
        "Wait, what's the difference between a list and a tuple?",
        "Why use a tuple if lists are more flexible?",
        "Can someone explain the syntax for a dictionary again?",
        "Is a tuple faster than a list in Python?",
        "When should I use a dictionary vs a list?",
    ],
    "ai_ml_rag": [
        "How does the AI remember what I said earlier?",
        "Does this system use a vector database for the memory?",
        "What happens if the RAG context is too long?",
        "Is the clustering happening in real-time?",
        "How do you calculate the centroid for a new question?",
    ],
    "general_interaction": [
        "This is a great explanation, thanks!",
        "The audio is a bit laggy for me.",
        "Hello from New York!",
        "Can you move the code up? I can't see the bottom.",
        "I'm lost, can we go back five minutes?",
    ],
    "career_backend": [
        "Is FastAPI better than Django for AI apps?",
        "What is the best way to scale these workers?",
        "How do I get a job as a Backend AI Engineer?",
        "Is Redis better than RabbitMQ for this pipeline?",
        "Do I need to know C++ for high-level system design?",
    ],
}

CLUSTER_NAMES = list(CLUSTERS.keys())

MOCK_AUTHORS = [
    "Rahul S",
    "Priya_codes",
    "TechLearner42",
    "student_2024",
    "CS_Enthusiast",
    "Amit Kumar",
    "DevNinja99",
    "Sneha R",
    "CodeNewbie_",
    "Arjun M",
    "Meera Dev",
    "hackathon_hero",
    "ByteMe_23",
    "Neha_learns",
    "SysAdmin_Sam",
]

# ---------------------------------------------------------------------------
# Comment generation
# ---------------------------------------------------------------------------

# Rotate primary cluster every N cycles to keep semantic density realistic
_CLUSTER_ROTATE_EVERY = 20
_current_primary_cluster: str = random.choice(CLUSTER_NAMES)
_cycle_counter = 0


def _maybe_rotate_cluster() -> None:
    global _current_primary_cluster, _cycle_counter
    _cycle_counter += 1
    if _cycle_counter % _CLUSTER_ROTATE_EVERY == 0:
        _current_primary_cluster = random.choice(CLUSTER_NAMES)
        logger.info(f"Rotated primary cluster to '{_current_primary_cluster}'")


def generate_mock_comment() -> dict:
    """Return a synthetic comment dict ready for DB insertion."""
    # 80% from primary cluster, 20% cross-cluster noise
    if random.random() < 0.8:
        cluster = _current_primary_cluster
    else:
        cluster = random.choice(CLUSTER_NAMES)

    text = random.choice(CLUSTERS[cluster])
    author = random.choice(MOCK_AUTHORS)

    return {
        "youtube_comment_id": f"mock:{uuid4()}",
        "author_name": author,
        "text": text,
        "published_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Poll / ingest
# ---------------------------------------------------------------------------


def mock_poll_session(session_id: str, manager: QueueManager, redis_client) -> None:
    """Generate one mock comment for a session and enqueue it."""
    for db in get_db_session():
        try:
            session = db.query(StreamingSession).filter_by(id=session_id).first()
            if not session or not session.is_active:
                return

            msg = generate_mock_comment()
            comment = Comment(
                session_id=session.id,
                youtube_comment_id=msg["youtube_comment_id"],
                author_name=msg["author_name"],
                text=msg["text"],
                published_at=msg["published_at"],
            )
            db.add(comment)
            db.flush()

            manager.enqueue(
                QUEUE_CLASSIFICATION,
                ClassificationPayload(
                    comment_id=str(comment.id),
                    text=comment.text,
                    session_id=str(session.id),
                ).to_dict(),
            )
            db.commit()

            # Publish event for WebSocket relay
            event = event_service.create_comment_created_event(
                {
                    "id": str(comment.id),
                    "text": comment.text,
                    "author_name": comment.author_name,
                    "session_id": str(session.id),
                }
            )
            redis_client.publish(f"ws:{session.id}", json.dumps(event))

            _stats["messages"] += 1
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Signal handling & main loop
# ---------------------------------------------------------------------------


def handle_signal(sig, frame):
    global _running
    logger.info("Shutdown signal received, stopping mock polling worker...")
    _running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def main() -> None:
    """Main mock polling loop — sequential, one comment per session per cycle."""
    global _running
    interval = settings.mock_message_interval

    logger.info(
        f"Starting MOCK YouTube polling worker... "
        f"(interval={interval}s, primary_cluster='{_current_primary_cluster}')"
    )
    manager = QueueManager()
    redis_client = get_redis_client()

    while _running:
        _stats["cycles"] += 1
        _maybe_rotate_cluster()

        # Log stats every 60s
        if time.time() - _stats["last_log"] >= 60:
            logger.info(
                f"Mock stats — cycles: {_stats['cycles']}, "
                f"messages: {_stats['messages']}, errors: {_stats['errors']}"
            )
            _stats["last_log"] = time.time()

        # Fetch active sessions (no youtube_video_id requirement)
        active_session_ids: list[str] = []
        for db in get_db_session():
            try:
                rows = db.query(StreamingSession.id).filter(StreamingSession.is_active.is_(True)).all()
                active_session_ids = [str(r.id) for r in rows]
            finally:
                db.close()

        for sid in active_session_ids:
            if not _running:
                break
            try:
                mock_poll_session(sid, manager, redis_client)
            except Exception as e:
                _stats["errors"] += 1
                logger.error(f"Mock poll error for session {sid}: {e}", exc_info=True)

        time.sleep(interval)

    logger.info("Mock YouTube polling worker shut down gracefully")
