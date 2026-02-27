"""Answer schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Optional


class AnswerBase(BaseModel):
    """Base answer schema."""

    text: str


class AnswerCreate(AnswerBase):
    """Answer creation schema."""

    cluster_id: UUID
    comment_id: Optional[UUID] = None


class AnswerUpdate(BaseModel):
    """Answer update schema."""

    text: Optional[str] = None


class AnswerResponse(AnswerBase):
    """Answer response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID
    comment_id: Optional[UUID]
    is_posted: bool
    posted_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
