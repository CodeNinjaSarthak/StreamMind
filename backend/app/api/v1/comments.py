"""Comments API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.db.models.comment import Comment
from app.db.models.streaming_session import StreamingSession
from app.db.models.teacher import Teacher
from app.schemas.comment import CommentResponse

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/{comment_id}", response_model=CommentResponse)
async def get_comment(
    comment_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CommentResponse:
    """Get a specific comment."""
    comment = (
        db.query(Comment)
        .join(StreamingSession, Comment.session_id == StreamingSession.id)
        .filter(
            Comment.id == comment_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment


@router.patch("/{comment_id}", response_model=CommentResponse)
async def mark_comment_answered(
    comment_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> CommentResponse:
    """Mark a comment as answered."""
    comment = (
        db.query(Comment)
        .join(StreamingSession, Comment.session_id == StreamingSession.id)
        .filter(
            Comment.id == comment_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    comment.is_answered = True
    db.commit()
    db.refresh(comment)
    return comment
