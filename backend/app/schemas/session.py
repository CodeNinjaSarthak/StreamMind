"""Session schemas."""

from uuid import UUID
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    """Session creation schema."""

    youtube_video_id: str
    title: Optional[str] = None
    description: Optional[str] = None


class SessionUpdate(BaseModel):
    """Session update schema."""

    title: Optional[str] = None
    description: Optional[str] = None


class SessionResponse(BaseModel):
    """Session response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    teacher_id: UUID
    youtube_video_id: str
    title: Optional[str]
    description: Optional[str]
    is_active: bool
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
