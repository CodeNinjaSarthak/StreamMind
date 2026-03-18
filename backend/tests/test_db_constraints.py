"""DB-level constraint tests via direct SQLAlchemy inserts."""

import uuid

import pytest
from app.db.models.comment import Comment
from app.db.models.streaming_session import StreamingSession
from app.db.models.teacher import Teacher
from sqlalchemy.exc import IntegrityError


def _create_session_in_db(db) -> str:
    """Insert a teacher + session directly, return session UUID string."""
    teacher = Teacher(
        email=f"constraint_{uuid.uuid4().hex[:8]}@test.com",
        name="Constraint Tester",
        hashed_password="fakehash",
    )
    db.add(teacher)
    db.flush()

    session = StreamingSession(
        teacher_id=teacher.id,
        youtube_video_id=f"vid_{uuid.uuid4().hex[:8]}",
    )
    db.add(session)
    db.flush()
    return str(session.id)


def test_comment_youtube_comment_id_not_null(db_session):
    session_id = _create_session_in_db(db_session)
    comment = Comment(
        session_id=session_id,
        youtube_comment_id=None,
        author_name="Test",
        text="Should fail",
    )
    db_session.add(comment)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_comment_youtube_comment_id_unique(db_session):
    session_id = _create_session_in_db(db_session)
    yt_id = f"dup_{uuid.uuid4().hex[:8]}"

    c1 = Comment(
        session_id=session_id,
        youtube_comment_id=yt_id,
        author_name="Test",
        text="First",
    )
    db_session.add(c1)
    db_session.flush()

    c2 = Comment(
        session_id=session_id,
        youtube_comment_id=yt_id,
        author_name="Test",
        text="Duplicate",
    )
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.flush()
