"""Streaming session model."""

import uuid
from datetime import (
    datetime,
    timezone,
)

from app.db.base import Base
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class StreamingSession(Base):
    """Streaming session database model."""

    __tablename__ = "streaming_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    youtube_video_id = Column(String(255), nullable=True, index=True)
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    teacher = relationship("Teacher", back_populates="streaming_sessions")
    comments = relationship("Comment", back_populates="session", cascade="all, delete-orphan")
    clusters = relationship("Cluster", back_populates="session", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_session_teacher_active", "teacher_id", "is_active"),
        Index("idx_session_youtube_video", "youtube_video_id"),
    )
