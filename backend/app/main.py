"""FastAPI application main entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1 import (
    answers,
    auth,
    clusters,
    comments,
    sessions,
    websocket,
    youtube,
)
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging
from backend.app.core.metrics import metrics_endpoint
from backend.app.core.middleware import RequestContextMiddleware

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="API for managing live doubt sessions with YouTube integration",
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

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(youtube.router, prefix=settings.api_v1_prefix)
app.include_router(sessions.router, prefix=settings.api_v1_prefix)
app.include_router(comments.router, prefix=settings.api_v1_prefix)
app.include_router(clusters.router, prefix=settings.api_v1_prefix)
app.include_router(answers.router, prefix=settings.api_v1_prefix)
app.include_router(websocket.router)


@app.get("/")
async def root() -> dict:
    """Root endpoint.

    Returns:
        API status.
    """
    return {
        "status": "ok",
        "message": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/health")
async def health() -> dict:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {
        "status": "ok",
        "health": "healthy",
        "environment": settings.environment
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint.

    Returns:
        Prometheus metrics.
    """
    from starlette.requests import Request
    request = Request(scope={"type": "http"})
    return await metrics_endpoint(request)


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            "environment": settings.environment,
            "debug": settings.debug
        }
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info(f"Shutting down {settings.app_name}")

