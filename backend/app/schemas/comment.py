"""Comment schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Optional


class CommentBase(BaseModel):
    """Base comment schema."""

    youtube_comment_id: str
    author_name: str
    text: str
    is_question: bool = False


class CommentCreate(CommentBase):
    """Comment creation schema."""

    session_id: UUID


class CommentResponse(CommentBase):
    """Comment response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    is_answered: bool
    created_at: datetime
    updated_at: datetime
