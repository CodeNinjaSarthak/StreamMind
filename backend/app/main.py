import sys
from pathlib import Path

# Add parent directory to Python path so we can import workers module
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

"""FastAPI application main entry point."""

import asyncio
import glob
import logging
import os

from app.api.v1 import (
    answers,
    auth,
    clusters,
    comments,
    dashboard,
)
from app.api.v1 import metrics as metrics_v1
from app.api.v1 import (
    rag,
    sessions,
    websocket,
    youtube,
)
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.metrics import metrics_endpoint
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit_middleware import RateLimitMiddleware
from app.services.websocket.manager import manager
from fastapi import (
    FastAPI,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="API for real-time YouTube teaching sessions with AI-powered Q&A",
    version=settings.app_version,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestContextMiddleware)

# RateLimitMiddleware added last so it wraps all other middleware (runs first on every request)
app.add_middleware(RateLimitMiddleware)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(metrics_v1.router, prefix=settings.api_v1_prefix)
app.include_router(youtube.router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router, prefix=settings.api_v1_prefix)
app.include_router(comments.router, prefix=settings.api_v1_prefix)
app.include_router(clusters.router, prefix=settings.api_v1_prefix)
app.include_router(answers.router, prefix=settings.api_v1_prefix)
app.include_router(rag.router, prefix=settings.api_v1_prefix + "/rag", tags=["rag"])
app.include_router(dashboard.router, prefix=settings.api_v1_prefix)
app.include_router(websocket.router)

# Serve frontend SPA if FRONTEND_DIR is configured
if settings.frontend_dir and os.path.isdir(settings.frontend_dir):
    app.mount("/app", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    logger.info(f"Serving frontend from {settings.frontend_dir} at /app")


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "status": "ok",
        "message": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "health": "healthy",
        "environment": settings.environment,
    }


@app.get("/metrics")
async def metrics(request: Request):
    """Prometheus metrics endpoint."""
    return await metrics_endpoint(request)


_relay_task: asyncio.Task | None = None


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    global _relay_task

    # Clear stale multiprocess metric files from previous runs
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR", "/tmp/prometheus_multiproc")
    for f in glob.glob(os.path.join(multiproc_dir, "*.db")):
        os.unlink(f)

    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={"environment": settings.environment, "debug": settings.debug},
    )
    _relay_task = asyncio.create_task(manager.start_subscriber())


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    global _relay_task
    if _relay_task:
        _relay_task.cancel()
    logger.info(f"Shutting down {settings.app_name}")
