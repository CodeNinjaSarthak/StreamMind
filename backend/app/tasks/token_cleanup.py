"""Token cleanup task — removes unrecoverable expired YouTube tokens."""

import logging
from datetime import (
    datetime,
    timezone,
)

from app.db.models.youtube_token import YouTubeToken
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def cleanup_expired_tokens(db: Session) -> None:
    """Delete YouTubeToken rows that are expired and have no refresh token.

    Tokens with a refresh_token can be renewed by the application — those are
    left alone. Only tokens that are both expired AND unrefreshable are removed.
    """
    now = datetime.now(timezone.utc)

    deleted = (
        db.query(YouTubeToken)
        .filter(
            YouTubeToken.expires_at <= now,
            YouTubeToken.refresh_token.is_(None),
        )
        .all()
    )

    if not deleted:
        logger.debug("No expired unrecoverable tokens found")
        return

    count = len(deleted)
    for token in deleted:
        db.delete(token)

    db.commit()
    logger.info(f"Deleted {count} expired unrecoverable YouTube token(s)")
