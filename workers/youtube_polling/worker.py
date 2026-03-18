"""YouTube Live Chat polling worker.

Polls all active sessions in parallel using ThreadPoolExecutor.
Each thread gets its own DB session and Redis client.
"""

import json
import logging
import os
import re
import signal
import sys
import time
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from datetime import datetime

# Ensure project root is on sys.path (for 'workers' package) and
# backend/ is on sys.path (for 'app' package).
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _project_root)
sys.path.insert(0, os.path.join(_project_root, "backend"))

from workers.common.prometheus_setup import setup_multiproc_dir  # noqa: E402

setup_multiproc_dir()

from app.core.encryption import (  # noqa: E402
    decrypt_data,
    encrypt_data,
)
from app.db.models.comment import Comment
from app.db.models.streaming_session import StreamingSession
from app.db.models.youtube_token import YouTubeToken
from app.services.websocket.events import event_service
from app.services.youtube.client import YouTubeClient
from app.services.youtube.oauth import YouTubeOAuthService
from app.services.youtube.quota import YouTubeQuotaService
from googleapiclient.errors import HttpError

from workers.common.db import get_db_session
from workers.common.metrics import (  # noqa: E402
    record_processing,
    update_queue_depths,
)
from workers.common.queue import (
    QUEUE_CLASSIFICATION,
    QueueManager,
)
from workers.common.redis import get_redis_client
from workers.common.schemas import ClassificationPayload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5  # seconds between full polling cycles


def strip_html_tags(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text)


_running = True
_stats = {"polls": 0, "messages": 0, "errors": 0, "last_log": time.time()}


def handle_signal(sig, frame):
    global _running
    logger.info("Shutdown signal received, stopping polling worker...")
    _running = False


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


def poll_session(session_id: str, manager: QueueManager) -> None:
    """Poll one session for new live chat messages.

    Gets its own DB session and Redis client. Checks quota before every API call.
    Only refreshes token when API returns 401.
    """
    redis_client = get_redis_client()
    quota_service = YouTubeQuotaService()

    for db in get_db_session():
        try:
            session = db.query(StreamingSession).filter_by(id=session_id).first()
            if not session or not session.is_active or not session.youtube_video_id:
                return

            token = db.query(YouTubeToken).filter_by(teacher_id=session.teacher_id).first()
            if not token:
                return

            teacher_id_str = str(session.teacher_id)
            chat_id_key = f"youtube:poll:{session_id}:chat_id"
            page_token_key = f"youtube:poll:{session_id}:page_token"

            access_token = decrypt_data(token.access_token)
            live_chat_id = redis_client.get(chat_id_key)

            # Get live_chat_id if not cached (costs quota)
            if not live_chat_id:
                if not quota_service.check_quota(teacher_id_str, "get_chat_id"):
                    logger.warning(f"Quota exceeded (get_chat_id) for teacher {teacher_id_str}")
                    return
                client = YouTubeClient(access_token)
                live_chat_id = client.get_live_chat_id(session.youtube_video_id)
                quota_service.record_usage(teacher_id_str, "get_chat_id")
                if not live_chat_id:
                    logger.warning(f"Video {session.youtube_video_id} not live, skipping")
                    return
                redis_client.setex(chat_id_key, 3600, live_chat_id)

            # Check quota before polling
            if not quota_service.check_quota(teacher_id_str, "poll"):
                logger.warning(f"Daily quota exceeded for teacher {teacher_id_str}, skipping poll")
                return

            page_token = redis_client.get(page_token_key)
            client = YouTubeClient(access_token)

            try:
                result = client.list_messages(live_chat_id, page_token)
                quota_service.record_usage(teacher_id_str, "poll")
            except HttpError as e:
                if e.resp.status == 401:
                    # Refresh on 401, retry once
                    oauth = YouTubeOAuthService()
                    refreshed = oauth.refresh_token(decrypt_data(token.refresh_token))
                    token.access_token = encrypt_data(refreshed["access_token"])
                    token.expires_at = refreshed.get("expires_at")
                    db.commit()
                    client = YouTubeClient(refreshed["access_token"])
                    result = client.list_messages(live_chat_id, page_token)
                    quota_service.record_usage(teacher_id_str, "poll")
                elif e.resp.status == 403:
                    logger.warning(f"YouTube API quota exceeded (HTTP 403) for session {session_id}")
                    return
                else:
                    raise

            fetched = 0
            for msg_data in result["messages"]:
                existing = db.query(Comment).filter_by(youtube_comment_id=msg_data["youtube_comment_id"]).first()
                if existing:
                    continue

                published_at = None
                if msg_data.get("published_at"):
                    published_at = datetime.fromisoformat(msg_data["published_at"].replace("Z", "+00:00"))

                comment = Comment(
                    session_id=session.id,
                    youtube_comment_id=msg_data["youtube_comment_id"],
                    author_name=strip_html_tags(msg_data["author_name"]),
                    author_channel_id=msg_data.get("author_channel_id"),
                    text=strip_html_tags(msg_data["text"]),
                    published_at=published_at,
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

                # Publish event for WebSocket relay
                ws_event = event_service.create_comment_created_event(
                    {
                        "id": str(comment.id),
                        "text": comment.text,
                        "author_name": comment.author_name,
                        "session_id": str(session.id),
                    }
                )
                redis_client.publish(f"ws:{session.id}", json.dumps(ws_event))

                fetched += 1

            db.commit()
            _stats["messages"] += fetched

            if result.get("next_page_token"):
                redis_client.setex(page_token_key, 3600, result["next_page_token"])

        finally:
            db.close()


def main() -> None:
    """Main polling loop."""
    global _running
    logger.info("Starting YouTube polling worker...")
    manager = QueueManager()

    while _running:
        _stats["polls"] += 1
        update_queue_depths(manager)

        # Log metrics every 60s
        if time.time() - _stats["last_log"] >= 60:
            logger.info(
                f"Polling stats — polls: {_stats['polls']}, "
                f"messages: {_stats['messages']}, errors: {_stats['errors']}"
            )
            _stats["last_log"] = time.time()

        active_session_ids = []
        for db in get_db_session():
            try:
                rows = (
                    db.query(StreamingSession.id)
                    .filter(
                        StreamingSession.is_active.is_(True),
                        StreamingSession.youtube_video_id.isnot(None),
                    )
                    .all()
                )
                active_session_ids = [str(r.id) for r in rows]
            finally:
                db.close()

        if active_session_ids:
            cycle_start = time.time()
            with ThreadPoolExecutor(max_workers=min(len(active_session_ids), 10)) as executor:
                futures = {executor.submit(poll_session, sid, manager): sid for sid in active_session_ids}
                cycle_success = True
                for future in as_completed(futures):
                    sid = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        cycle_success = False
                        _stats["errors"] += 1
                        logger.error(f"Poll error for session {sid}: {e}", exc_info=True)
            record_processing("youtube_polling", time.time() - cycle_start, cycle_success)

        time.sleep(POLL_INTERVAL)

    logger.info("YouTube polling worker shut down gracefully")


if __name__ == "__main__":
    from app.core.config import settings

    if settings.mock_youtube:
        from workers.youtube_polling.mock_worker import main as mock_main

        mock_main()
    else:
        main()
