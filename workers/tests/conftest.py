"""Shared fixtures for worker tests."""

import os
import uuid
from unittest.mock import MagicMock

import fakeredis
import pytest
from sqlalchemy import (
    create_engine,
    event,
    text,
)
from sqlalchemy.orm import sessionmaker

from workers.common.queue import QueueManager

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
    from app.db.models import (  # noqa: F401
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


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate all tables between tests for isolation."""
    yield
    db = TestingSessionLocal()
    try:
        db.execute(
            text(
                "TRUNCATE answers, comments, clusters, streaming_sessions, "
                "teachers, youtube_tokens, quotas, rag_documents CASCADE"
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


@pytest.fixture()
def fake_redis():
    """Fresh fakeredis instance per test, decode_responses=True to match production."""
    r = fakeredis.FakeRedis(decode_responses=True)
    yield r
    r.flushall()


@pytest.fixture()
def queue_manager(fake_redis):
    """QueueManager wired to fakeredis."""
    return QueueManager(redis_client=fake_redis)


@pytest.fixture()
def gemini_mock():
    """Function-scoped mock GeminiClient with sane defaults."""
    mock = MagicMock()
    mock.classify_question.return_value = {"is_question": True, "confidence": 0.95}
    mock.generate_embedding.return_value = [0.1] * 768
    mock._circuit_breaker = MagicMock()
    mock._circuit_breaker.ensure_closed.return_value = None
    return mock


@pytest.fixture()
def test_teacher(db_session):
    """Create a minimal Teacher row for FK constraints."""
    from app.db.models.teacher import Teacher

    teacher = Teacher(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@test.com",
        name="Test Teacher",
        hashed_password="fakehash",
    )
    db_session.add(teacher)
    db_session.commit()
    return teacher


@pytest.fixture()
def test_session(db_session, test_teacher):
    """Create a minimal StreamingSession row for FK constraints."""
    from app.db.models.streaming_session import StreamingSession

    session = StreamingSession(
        id=uuid.uuid4(),
        teacher_id=test_teacher.id,
        youtube_video_id=f"test_video_{uuid.uuid4().hex[:8]}",
    )
    db_session.add(session)
    db_session.commit()
    return session


@pytest.fixture()
def test_comment(db_session, test_session):
    """Create a minimal Comment row for pipeline tests."""
    from app.db.models.comment import Comment

    comment = Comment(
        id=uuid.uuid4(),
        session_id=test_session.id,
        youtube_comment_id=f"manual:{uuid.uuid4()}",
        author_name="Student",
        text="How does backpropagation work?",
    )
    db_session.add(comment)
    db_session.commit()
    return comment
