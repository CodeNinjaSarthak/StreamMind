"""Quota model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Quota(Base):
    """Quota database model."""

    __tablename__ = "quotas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True)
    quota_type = Column(String(50), nullable=False)
    used = Column(Integer, default=0, nullable=False)
    limit = Column(Integer, nullable=False)
    period = Column(String(20), nullable=False)
    reset_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    teacher = relationship("Teacher", back_populates="quotas")

    __table_args__ = (
        UniqueConstraint("teacher_id", "quota_type", "period", name="uq_teacher_quota_period"),
        Index("idx_quota_teacher_type", "teacher_id", "quota_type"),
    )
