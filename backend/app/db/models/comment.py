"""Comment model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from backend.app.db.base import Base


class Comment(Base):
    """Comment database model."""

    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("streaming_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    cluster_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clusters.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    youtube_comment_id = Column(String(255), unique=True, index=True, nullable=False)
    author_name = Column(String(255), nullable=False)
    author_channel_id = Column(String(255), nullable=True)
    text = Column(Text, nullable=False)
    is_question = Column(Boolean, default=False, nullable=False)
    is_answered = Column(Boolean, default=False, nullable=False)
    confidence_score = Column(Float, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    session = relationship("StreamingSession", back_populates="comments")
    cluster = relationship("Cluster", back_populates="comments")
    answers = relationship("Answer", back_populates="comment")

    __table_args__ = (
        Index("idx_comment_session_question", "session_id", "is_question"),
        Index("idx_comment_session_answered", "session_id", "is_answered"),
        Index("idx_comment_cluster", "cluster_id"),
    )

