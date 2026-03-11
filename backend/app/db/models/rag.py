"""RAG (Retrieval Augmented Generation) model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class RAGDocument(Base):
    """RAG document database model."""

    __tablename__ = "rag_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source_type = Column(String(50), nullable=True)
    source_url = Column(String(1000), nullable=True)
    doc_metadata = Column("metadata", JSONB, nullable=True)
    embedding = Column(Vector(768), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    teacher = relationship("Teacher", back_populates="rag_documents")

    __table_args__ = (Index("idx_rag_source_type", "source_type"),)
