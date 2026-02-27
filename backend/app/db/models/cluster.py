"""Cluster model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class Cluster(Base):
    """Cluster database model."""

    __tablename__ = "clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("streaming_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    similarity_threshold = Column(Float, default=0.8, nullable=False)
    centroid_embedding = Column(Vector(1536), nullable=True)
    comment_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    session = relationship("StreamingSession", back_populates="clusters")
    comments = relationship("Comment", back_populates="cluster")
    answers = relationship("Answer", back_populates="cluster", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_cluster_session", "session_id"),
    )

