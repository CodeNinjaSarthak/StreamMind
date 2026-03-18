"""YouTube OAuth and video API routes."""

import json
import logging

import redis as redis_lib
from app.core.config import settings
from app.core.encryption import (
    decrypt_data,
    encrypt_data,
)
from app.core.security import get_current_active_user
from app.db.models.teacher import Teacher
from app.db.models.youtube_token import YouTubeToken
from app.db.session import get_db
from app.services.youtube.client import YouTubeClient
from app.services.youtube.oauth import YouTubeOAuthService
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import (
    HTMLResponse,
)
from sqlalchemy.orm import Session

router = APIRouter(prefix="/youtube", tags=["youtube"])
logger = logging.getLogger(__name__)

_redis = redis_lib.from_url(settings.redis_url, decode_responses=True)

_OAUTH_SUCCESS_HTML = """<!DOCTYPE html>
<html>
<body>
<script>
  if (window.opener) {
    window.opener.postMessage(
      {type: 'youtube_oauth_complete', status: 'success'},
      window.location.origin
    );
    window.close();
  } else {
    window.location.href = '/app';
  }
</script>
<p>YouTube connected! You can close this window.</p>
</body>
</html>"""


@router.get("/auth/url")
async def get_auth_url(
    return_url: str = Query(default="/app"),
    current_user: Teacher = Depends(get_current_active_user),
) -> dict:
    """Generate YouTube OAuth authorization URL.

    Stores {teacher_id, return_url, url} in Redis with 10-min TTL (CSRF protection).
    If an active state already exists for this teacher, returns the existing URL
    to prevent race conditions.
    """
    teacher_id_str = str(current_user.id)

    # Race-condition prevention: reuse existing state if still valid
    existing_state = _redis.get(f"yt_state_teacher:{teacher_id_str}")
    if existing_state:
        state_data_raw = _redis.get(f"yt_state:{existing_state}")
        if state_data_raw:
            state_data = json.loads(state_data_raw)
            return {"url": state_data["url"], "state": existing_state}

    oauth_service = YouTubeOAuthService()
    url, state = oauth_service.get_authorization_url()

    payload = {
        "teacher_id": teacher_id_str,
        "return_url": return_url,
        "url": url,
    }
    _redis.setex(f"yt_state:{state}", 600, json.dumps(payload))
    _redis.setex(f"yt_state_teacher:{teacher_id_str}", 600, state)

    return {"url": url, "state": state}


@router.get("/auth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Handle YouTube OAuth callback.

    Verifies CSRF state, exchanges code for tokens, encrypts and stores them,
    then returns an HTML page that posts a message to the opener window.
    """
    state_data_raw = _redis.get(f"yt_state:{state}")
    if not state_data_raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    data = json.loads(state_data_raw)

    oauth_service = YouTubeOAuthService()
    try:
        token_data = oauth_service.exchange_code_for_token(code)
    except Exception as e:
        logger.error(f"OAuth token exchange failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to exchange authorization code",
        )

    from uuid import UUID

    teacher_id = UUID(data["teacher_id"])

    existing_token = db.query(YouTubeToken).filter(YouTubeToken.teacher_id == teacher_id).first()
    if existing_token:
        existing_token.access_token = encrypt_data(token_data["access_token"])
        if token_data.get("refresh_token"):
            existing_token.refresh_token = encrypt_data(token_data["refresh_token"])
        existing_token.expires_at = token_data.get("expires_at")
        existing_token.scope = token_data.get("scope", "")
    else:
        new_token = YouTubeToken(
            teacher_id=teacher_id,
            access_token=encrypt_data(token_data["access_token"]),
            refresh_token=encrypt_data(token_data["refresh_token"]) if token_data.get("refresh_token") else "",
            expires_at=token_data.get("expires_at"),
            scope=token_data.get("scope", ""),
        )
        db.add(new_token)

    db.commit()
    logger.info(f"YouTube token stored for teacher {teacher_id}")

    # Delete Redis state after successful DB commit — if this fails, keys expire via TTL
    _redis.delete(f"yt_state:{state}")
    _redis.delete(f"yt_state_teacher:{data['teacher_id']}")

    return HTMLResponse(content=_OAUTH_SUCCESS_HTML)


@router.post("/auth/refresh")
async def refresh_token(
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Refresh YouTube access token."""
    token = db.query(YouTubeToken).filter(YouTubeToken.teacher_id == current_user.id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No YouTube token found",
        )

    try:
        decrypted_refresh = decrypt_data(token.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YouTube token is invalid or corrupted. Please reconnect your YouTube account.",
        )

    oauth_service = YouTubeOAuthService()
    try:
        refreshed = oauth_service.refresh_token(decrypted_refresh)
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to refresh token",
        )

    token.access_token = encrypt_data(refreshed["access_token"])
    token.expires_at = refreshed.get("expires_at")
    db.commit()

    return {"status": "refreshed"}


@router.get("/auth/status")
async def get_auth_status(
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get YouTube connection status."""
    token = db.query(YouTubeToken).filter(YouTubeToken.teacher_id == current_user.id).first()
    if not token:
        return {"connected": False, "expires_at": None}

    expires_at_str = None
    if token.expires_at:
        expires_at_str = (
            token.expires_at.isoformat() if hasattr(token.expires_at, "isoformat") else str(token.expires_at)
        )
    return {"connected": True, "expires_at": expires_at_str}


@router.delete("/auth/disconnect", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_youtube(
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete YouTube token (disconnect)."""
    token = db.query(YouTubeToken).filter(YouTubeToken.teacher_id == current_user.id).first()
    if token:
        db.delete(token)
        db.commit()


@router.get("/videos/{video_id}")
async def get_video_info(
    video_id: str,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get video title and live chat status via teacher's token."""
    token = db.query(YouTubeToken).filter(YouTubeToken.teacher_id == current_user.id).first()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YouTube not connected",
        )

    try:
        access_token = decrypt_data(token.access_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YouTube token is invalid or corrupted. Please reconnect your YouTube account.",
        )

    client = YouTubeClient(access_token)
    try:
        info = client.get_video_info(video_id)
    except Exception as e:
        logger.error(f"Failed to get video info for {video_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve video info",
        )

    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found",
        )
    return info


@router.get("/videos/{video_id}/validate")
async def validate_video(
    video_id: str,
    current_user: Teacher = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict:
    """Validate a video ID and check if it is a live stream."""
    token = db.query(YouTubeToken).filter(YouTubeToken.teacher_id == current_user.id).first()
    if not token:
        return {"valid": False, "is_live": False, "title": ""}

    try:
        access_token = decrypt_data(token.access_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="YouTube token is invalid or corrupted. Please reconnect your YouTube account.",
        )

    client = YouTubeClient(access_token)
    try:
        info = client.get_video_info(video_id)
    except Exception:
        return {"valid": False, "is_live": False, "title": ""}

    if not info:
        return {"valid": False, "is_live": False, "title": ""}

    return {
        "valid": True,
        "is_live": info.get("is_live", False),
        "title": info.get("title", ""),
    }
