"""Auth-gated JSON metrics endpoint."""

from app.core.security import get_current_active_user
from app.db.models.answer import Answer
from app.db.models.cluster import Cluster
from app.db.models.comment import Comment
from app.db.models.streaming_session import StreamingSession
from app.db.models.teacher import Teacher
from app.db.session import get_db
from fastapi import (
    APIRouter,
    Depends,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get metrics scoped to current teacher. Requires authentication.

    Returns:
        Dict with active_sessions, questions_processed, and answers_generated counts.
    """
    active_sessions = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.teacher_id == current_user.id,
            StreamingSession.is_active.is_(True),
        )
        .count()
    )

    questions_processed = (
        db.query(Comment)
        .join(StreamingSession, Comment.session_id == StreamingSession.id)
        .filter(StreamingSession.teacher_id == current_user.id)
        .count()
    )

    answers_generated = (
        db.query(Answer)
        .join(Cluster, Answer.cluster_id == Cluster.id)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(StreamingSession.teacher_id == current_user.id)
        .count()
    )

    return {
        "active_sessions": active_sessions,
        "questions_processed": questions_processed,
        "answers_generated": answers_generated,
    }
