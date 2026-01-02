"""Comments API routes."""

from fastapi import APIRouter

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/")
async def list_comments(session_id: int) -> dict:
    """List comments for a session.

    Args:
        session_id: Session ID.

    Returns:
        Comments list response.
    """
    return {"status": "ok"}


@router.get("/{comment_id}")
async def get_comment(comment_id: int) -> dict:
    """Get a specific comment.

    Args:
        comment_id: Comment ID.

    Returns:
        Comment response.
    """
    return {"status": "ok"}


@router.post("/{comment_id}/mark-answered")
async def mark_comment_answered(comment_id: int) -> dict:
    """Mark a comment as answered.

    Args:
        comment_id: Comment ID.

    Returns:
        Status response.
    """
    return {"status": "ok"}

