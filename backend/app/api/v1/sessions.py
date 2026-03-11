"""Streaming sessions API routes."""

from datetime import datetime, timezone
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.db.models.streaming_session import StreamingSession
from app.db.models.comment import Comment
from app.db.models.cluster import Cluster
from app.db.models.answer import Answer
from app.db.models.teacher import Teacher
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse, SessionAnalyticsResponse
from app.schemas.comment import CommentResponse
from app.schemas.cluster import ClusterResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Create a new streaming session."""
    session = StreamingSession(
        teacher_id=current_user.id,
        youtube_video_id=payload.youtube_video_id,
        title=payload.title,
        description=payload.description,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[SessionResponse]:
    """List all streaming sessions for the current user."""
    sessions = (
        db.query(StreamingSession)
        .filter(StreamingSession.teacher_id == current_user.id)
        .order_by(StreamingSession.created_at.desc())
        .all()
    )
    return sessions


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Get a specific streaming session."""
    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: UUID,
    payload: SessionUpdate,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    """Update a streaming session's title or description."""
    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, field, value)

    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    """End a streaming session."""
    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.is_active = False
    session.ended_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}/comments", response_model=List[CommentResponse])
async def list_session_comments(
    session_id: UUID,
    limit: int = 100,
    offset: int = 0,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[CommentResponse]:
    """List comments for a session with pagination."""
    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    comments = db.query(Comment).filter(Comment.session_id == session_id).offset(offset).limit(limit).all()
    return comments


@router.get("/{session_id}/clusters", response_model=List[ClusterResponse])
async def list_session_clusters(
    session_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[ClusterResponse]:
    """List all clusters for a session."""
    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    clusters = db.query(Cluster).options(selectinload(Cluster.answers)).filter(Cluster.session_id == session_id).all()
    return clusters


@router.get("/{session_id}/analytics", response_model=SessionAnalyticsResponse)
async def get_session_analytics(
    session_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return aggregate analytics for a session."""
    session = (
        db.query(StreamingSession)
        .filter(
            StreamingSession.id == session_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Totals
    total_questions = db.query(Comment).filter(Comment.session_id == session_id, Comment.is_question == True).count()

    clusters = db.query(Cluster).filter(Cluster.session_id == session_id).all()
    total_clusters = len(clusters)
    avg_cluster_size = sum(c.comment_count for c in clusters) / total_clusters if total_clusters > 0 else 0.0

    # Clusters with at least one posted answer
    clusters_answered = (
        db.query(func.count(func.distinct(Answer.cluster_id)))
        .join(Cluster, Answer.cluster_id == Cluster.id)
        .filter(
            Cluster.session_id == session_id,
            Answer.is_posted == True,
        )
        .scalar()
        or 0
    )
    response_rate = clusters_answered / total_clusters if total_clusters > 0 else 0.0

    # Hourly question buckets (UTC)
    hourly_rows = (
        db.query(
            func.date_trunc("hour", Comment.created_at).label("hour"),
            func.count().label("count"),
        )
        .filter(Comment.session_id == session_id, Comment.is_question == True)
        .group_by(func.date_trunc("hour", Comment.created_at))
        .order_by(func.date_trunc("hour", Comment.created_at))
        .all()
    )

    questions_over_time = [{"hour": row.hour.isoformat(), "count": row.count} for row in hourly_rows]

    peak_hour = None
    if hourly_rows:
        peak = max(hourly_rows, key=lambda r: r.count)
        peak_hour = peak.hour.isoformat()

    # Top 5 clusters by comment_count
    top_clusters = sorted(clusters, key=lambda c: c.comment_count, reverse=True)[:5]

    return {
        "total_questions": total_questions,
        "total_clusters": total_clusters,
        "response_rate": round(response_rate, 2),
        "avg_cluster_size": round(avg_cluster_size, 1),
        "peak_hour": peak_hour,
        "questions_over_time": questions_over_time,
        "top_clusters": [{"title": c.title, "comment_count": c.comment_count} for c in top_clusters],
    }
