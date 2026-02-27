"""Streaming sessions API routes."""

from datetime import datetime, timezone
from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.db.models.streaming_session import StreamingSession
from app.db.models.comment import Comment
from app.db.models.cluster import Cluster
from app.db.models.teacher import Teacher
from app.schemas.session import SessionCreate, SessionUpdate, SessionResponse
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
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[CommentResponse]:
    """List all comments for a session."""
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

    comments = db.query(Comment).filter(Comment.session_id == session_id).all()
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

    clusters = db.query(Cluster).filter(Cluster.session_id == session_id).all()
    return clusters
