"""Payload schemas for worker queues."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID


@dataclass
class CommentIngestPayload:
    """Payload for comment ingestion queue."""

    session_id: str
    youtube_comment_id: str
    author_name: str
    text: str
    author_channel_id: Optional[str] = None
    published_at: Optional[str] = None
    task_id: Optional[str] = None
    created_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "youtube_comment_id": self.youtube_comment_id,
            "author_name": self.author_name,
            "text": self.text,
            "author_channel_id": self.author_channel_id,
            "published_at": self.published_at,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


@dataclass
class ClassificationPayload:
    """Payload for comment classification queue."""

    comment_id: str
    text: str
    session_id: str
    task_id: Optional[str] = None
    created_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "comment_id": self.comment_id,
            "text": self.text,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


@dataclass
class EmbeddingPayload:
    """Payload for embedding generation queue."""

    comment_id: str
    text: str
    task_id: Optional[str] = None
    created_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "comment_id": self.comment_id,
            "text": self.text,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


@dataclass
class ClusteringPayload:
    """Payload for clustering queue."""

    session_id: str
    comment_ids: List[str]
    trigger_type: str = "manual"
    task_id: Optional[str] = None
    created_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "comment_ids": self.comment_ids,
            "trigger_type": self.trigger_type,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


@dataclass
class AnswerGenerationPayload:
    """Payload for answer generation queue."""

    cluster_id: str
    session_id: str
    question_texts: List[str]
    task_id: Optional[str] = None
    created_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cluster_id": self.cluster_id,
            "session_id": self.session_id,
            "question_texts": self.question_texts,
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }
