"""Shared test fixtures: test DB, async client, auth helpers."""

import os
import uuid
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import (
    ASGITransport,
    AsyncClient,
)
from sqlalchemy import (
    create_engine,
    event,
    text,
)
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("GEMINI_API_KEY", "test-key-placeholder")

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://sarthak@localhost:5432/ai_doubt_manager_test",
)

engine = create_engine(TEST_DATABASE_URL, echo=False)


@event.listens_for(engine, "connect")
def _enable_pgvector(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except Exception:
        pass
    finally:
        cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create all tables once per test session, drop after."""
    from app.db.base import Base
    from app.db.models import (  # noqa: F401 — force model registration
        Answer,
        Cluster,
        Comment,
        Quota,
        RAGDocument,
        StreamingSession,
        Teacher,
        YouTubeToken,
    )

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate all tables between tests for isolation."""
    yield
    db = TestingSessionLocal()
    try:
        db.execute(
            text(
                "TRUNCATE answers, comments, clusters, streaming_sessions, teachers, youtube_tokens, quotas, rag_documents CASCADE"
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def db_session():
    """Provide a raw SQLAlchemy session for DB-level tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest_asyncio.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the FastAPI app with test DB + mocked Redis."""
    from app.db.session import get_db
    from app.main import app

    app.dependency_overrides[get_db] = _override_get_db

    with (
        patch("app.services.token_blacklist.token_blacklist.is_blacklisted", return_value=False),
        patch("app.services.token_blacklist.token_blacklist.blacklist_token"),
        patch("app.core.rate_limit_middleware.RateLimitMiddleware.dispatch", side_effect=_passthrough_dispatch),
        patch("workers.common.queue.QueueManager.enqueue", return_value=None),
        patch("app.services.websocket.manager.manager.start_subscriber", return_value=None),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


async def _passthrough_dispatch(request, call_next):
    """Bypass rate limiting in tests."""
    return await call_next(request)


# ---------------------------------------------------------------------------
# Auth helper fixtures
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str, name: str, password: str) -> dict:
    """Register a teacher and log in, return auth headers."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture()
async def auth_headers(client: AsyncClient) -> dict:
    """Register + login Teacher A, return Bearer headers."""
    return await _register_and_login(client, "teacher_a@test.com", "Teacher A", "password123")


@pytest_asyncio.fixture()
async def second_auth_headers(client: AsyncClient) -> dict:
    """Register + login Teacher B, return Bearer headers."""
    return await _register_and_login(client, "teacher_b@test.com", "Teacher B", "password456")


@pytest_asyncio.fixture()
async def session_id(client: AsyncClient, auth_headers: dict) -> str:
    """Create a streaming session for Teacher A, return its UUID string."""
    resp = await client.post(
        "/api/v1/sessions/",
        json={"youtube_video_id": f"test_video_{uuid.uuid4().hex[:8]}"},
        headers=auth_headers,
    )
    return resp.json()["id"]
