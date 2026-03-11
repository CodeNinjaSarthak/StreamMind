"""YouTube API schemas."""

from pydantic import BaseModel
from typing import Optional


class YouTubeAuthRequest(BaseModel):
    """YouTube OAuth request schema."""

    code: str


class YouTubeAuthResponse(BaseModel):
    """YouTube OAuth response schema."""

    status: str
    access_token: Optional[str] = None


class YouTubeVideoInfo(BaseModel):
    """YouTube video information schema."""

    video_id: str
    title: Optional[str] = None
    channel_id: Optional[str] = None
