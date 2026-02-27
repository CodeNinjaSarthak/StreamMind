"""Clusters API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.db.models.cluster import Cluster
from app.db.models.streaming_session import StreamingSession
from app.db.models.teacher import Teacher
from app.schemas.cluster import ClusterResponse, ClusterUpdate

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: UUID,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ClusterResponse:
    """Get a specific cluster."""
    cluster = (
        db.query(Cluster)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Cluster.id == cluster_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")
    return cluster


@router.patch("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: UUID,
    payload: ClusterUpdate,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ClusterResponse:
    """Update a cluster's title or description."""
    cluster = (
        db.query(Cluster)
        .join(StreamingSession, Cluster.session_id == StreamingSession.id)
        .filter(
            Cluster.id == cluster_id,
            StreamingSession.teacher_id == current_user.id,
        )
        .first()
    )
    if not cluster:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cluster, field, value)

    db.commit()
    db.refresh(cluster)
    return cluster
