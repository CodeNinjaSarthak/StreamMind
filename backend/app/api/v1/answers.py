"""Answers API routes."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.db.models.answer import Answer
from app.db.models.cluster import Cluster
from app.db.models.streaming_session import StreamingSession
from app.db.models.teacher import Teacher
from app.schemas.answer import AnswerCreate, AnswerResponse, AnswerUpdate

router = APIRouter(prefix="/answers", tags=["answers"])


@router.post("/", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
async def create_answer(
    payload: AnswerCreate,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    """Create a new answer for a cluster."""
    cluster = (
        db.query(Cluster)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Cluster.id == payload.cluster_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")

    answer = Answer(
        cluster_id=payload.cluster_id,
        comment_id=payload.comment_id,
        text=payload.text,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


@router.get("/{answer_id}", response_model=AnswerResponse)
async def get_answer(
    answer_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    """Get a specific answer."""
    answer = (
        db.query(Answer)
        .join(Cluster, Answer.cluster_id == Cluster.id)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Answer.id == answer_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
    return answer


@router.patch("/{answer_id}", response_model=AnswerResponse)
async def update_answer(
    answer_id: UUID,
    payload: AnswerUpdate,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    """Update an answer's text."""
    answer = (
        db.query(Answer)
        .join(Cluster, Answer.cluster_id == Cluster.id)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Answer.id == answer_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(answer, field, value)

    db.commit()
    db.refresh(answer)
    return answer


@router.post("/{answer_id}/post", response_model=AnswerResponse)
async def post_answer(
    answer_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> AnswerResponse:
    """Mark an answer as posted to YouTube Live Chat."""
    answer = (
        db.query(Answer)
        .join(Cluster, Answer.cluster_id == Cluster.id)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Answer.id == answer_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not answer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")

    answer.is_posted = True
    answer.posted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(answer)
    return answer
