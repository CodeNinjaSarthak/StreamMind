"""Session schemas."""

from datetime import datetime
from typing import (
    List,
    Optional,
)
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
)


class SessionCreate(BaseModel):
    """Session creation schema."""

    youtube_video_id: Optional[str] = None
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
    youtube_video_id: Optional[str]
    title: Optional[str]
    description: Optional[str]
    is_active: bool
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class HourlyCount(BaseModel):
    hour: str  # ISO datetime string for tz-aware frontend formatting
    count: int


class TopCluster(BaseModel):
    title: str
    comment_count: int


class SessionAnalyticsResponse(BaseModel):
    total_questions: int
    total_clusters: int
    response_rate: float  # clusters_with_posted_answer / total_clusters
    avg_cluster_size: float
    peak_hour: Optional[str]  # ISO datetime string or None
    questions_over_time: List[HourlyCount]
    top_clusters: List[TopCluster]  # top 5 by comment_count
