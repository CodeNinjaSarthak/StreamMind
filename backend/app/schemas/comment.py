"""Comment schemas."""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class CommentBase(BaseModel):
    """Base comment schema."""

    youtube_comment_id: str
    author_name: str
    text: str
    is_question: bool = False


class CommentCreate(CommentBase):
    """Comment creation schema."""

    session_id: int


class CommentResponse(CommentBase):
    """Comment response schema."""

    id: int
    session_id: int
    is_answered: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True

