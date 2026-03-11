"""Auth-gated JSON metrics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.models.answer import Answer
from app.db.models.comment import Comment
from app.db.models.streaming_session import StreamingSession
from app.db.models.teacher import Teacher
from app.db.session import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def get_metrics(
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get system metrics. Requires authentication.

    Returns:
        Dict with active_sessions, questions_processed, and answers_generated counts.
    """
    return {
        "active_sessions": db.query(StreamingSession).filter(StreamingSession.is_active == True).count(),
        "questions_processed": db.query(Comment).count(),
        "answers_generated": db.query(Answer).count(),
    }
