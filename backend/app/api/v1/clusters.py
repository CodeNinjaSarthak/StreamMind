"""Clusters API routes."""

from fastapi import APIRouter

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("/")
async def list_clusters(session_id: int) -> dict:
    """List clusters for a session.

    Args:
        session_id: Session ID.

    Returns:
        Clusters list response.
    """
    return {"status": "ok"}


@router.get("/{cluster_id}")
async def get_cluster(cluster_id: int) -> dict:
    """Get a specific cluster.

    Args:
        cluster_id: Cluster ID.

    Returns:
        Cluster response.
    """
    return {"status": "ok"}


@router.post("/")
async def create_cluster() -> dict:
    """Create a new cluster.

    Returns:
        Cluster creation response.
    """
    return {"status": "ok"}

