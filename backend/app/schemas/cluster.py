"""Cluster schemas."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict
from typing import Optional


class ClusterBase(BaseModel):
    """Base cluster schema."""

    title: str
    description: Optional[str] = None
    similarity_threshold: float


class ClusterCreate(ClusterBase):
    """Cluster creation schema."""

    session_id: UUID


class ClusterUpdate(BaseModel):
    """Cluster update schema."""

    title: Optional[str] = None
    description: Optional[str] = None


class ClusterResponse(ClusterBase):
    """Cluster response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID
    created_at: datetime
    updated_at: datetime
