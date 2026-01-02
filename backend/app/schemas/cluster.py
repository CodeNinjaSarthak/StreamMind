"""Cluster schemas."""

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ClusterBase(BaseModel):
    """Base cluster schema."""

    title: str
    description: Optional[str] = None
    similarity_threshold: float


class ClusterCreate(ClusterBase):
    """Cluster creation schema."""

    session_id: int


class ClusterResponse(ClusterBase):
    """Cluster response schema."""

    id: int
    session_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True

