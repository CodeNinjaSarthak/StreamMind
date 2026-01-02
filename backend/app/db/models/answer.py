"""Answer model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


class Answer(Base):
    """Answer database model."""

    __tablename__ = "answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    cluster_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clusters.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    comment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    text = Column(Text, nullable=False)
    youtube_comment_id = Column(String(255), nullable=True, unique=True)
    is_posted = Column(Boolean, default=False, nullable=False)
    posted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    cluster = relationship("Cluster", back_populates="answers")
    comment = relationship("Comment", back_populates="answers")

    __table_args__ = (
        Index("idx_answer_cluster_posted", "cluster_id", "is_posted"),
    )

