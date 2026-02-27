"""YouTube API routes."""

from fastapi import APIRouter

from app.schemas.youtube import YouTubeAuthRequest, YouTubeAuthResponse

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/auth-url")
async def get_auth_url() -> dict:
    """Get YouTube OAuth authorization URL.

    Returns:
        Authorization URL response.
    """
    return {"status": "ok"}


@router.post("/auth", response_model=YouTubeAuthResponse)
async def authenticate(request: YouTubeAuthRequest) -> dict:
    """Authenticate with YouTube OAuth.

    Args:
        request: OAuth request with authorization code.

    Returns:
        Authentication response.
    """
    return {"status": "ok"}


@router.get("/videos/{video_id}")
async def get_video_info(video_id: str) -> dict:
    """Get YouTube video information.

    Args:
        video_id: YouTube video ID.

    Returns:
        Video information response.
    """
    return {"status": "ok"}

