"""Answer schemas."""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class AnswerBase(BaseModel):
    """Base answer schema."""

    text: str


class AnswerCreate(AnswerBase):
    """Answer creation schema."""

    cluster_id: int
    comment_id: Optional[int] = None


class AnswerResponse(AnswerBase):
    """Answer response schema."""

    id: int
    cluster_id: int
    comment_id: Optional[int]
    is_posted: bool
    posted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True

