"""Scheduler task behaviour tests.

Tests the CONTRACT of each task function:
- reset_quotas: zeroes used counts, advances reset_at, leaves future quotas alone
- cleanup_expired_tokens: removes unrecoverable expired tokens, leaves refreshable ones

All tests are sync, use real test DB (db_session fixture), no mocking needed.
"""

import uuid
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from app.tasks.quota_reset import reset_quotas
from app.tasks.token_cleanup import cleanup_expired_tokens

# ---------------------------------------------------------------------------
# reset_quotas behaviour
# ---------------------------------------------------------------------------


def test_expired_daily_quota_is_reset(db_session, test_teacher):
    """A daily quota past its reset_at has used zeroed and reset_at advanced by 1 day."""
    from app.db.models.quota import Quota

    now = datetime.now(timezone.utc)
    quota = Quota(
        id=uuid.uuid4(),
        teacher_id=test_teacher.id,
        quota_type="daily_answer",
        used=47,
        limit=100,
        period="daily",
        reset_at=now - timedelta(hours=1),
    )
    db_session.add(quota)
    db_session.commit()

    reset_quotas(db_session)

    db_session.refresh(quota)
    assert quota.used == 0
    assert quota.reset_at > now


def test_future_quota_is_not_touched(db_session, test_teacher):
    """A quota whose reset_at is in the future is left completely alone."""
    from app.db.models.quota import Quota

    now = datetime.now(timezone.utc)
    original_used = 15
    future_reset = now + timedelta(hours=12)

    quota = Quota(
        id=uuid.uuid4(),
        teacher_id=test_teacher.id,
        quota_type="daily_answer",
        used=original_used,
        limit=100,
        period="daily",
        reset_at=future_reset,
    )
    db_session.add(quota)
    db_session.commit()

    reset_quotas(db_session)

    db_session.refresh(quota)
    assert quota.used == original_used
    assert quota.reset_at == future_reset


def test_monthly_quota_reset_advances_by_30_days(db_session, test_teacher):
    """A monthly quota's reset_at is advanced by 30 days after reset."""
    from app.db.models.quota import Quota

    now = datetime.now(timezone.utc)
    quota = Quota(
        id=uuid.uuid4(),
        teacher_id=test_teacher.id,
        quota_type="monthly_session",
        used=10,
        limit=30,
        period="monthly",
        reset_at=now - timedelta(days=1),
    )
    db_session.add(quota)
    db_session.commit()

    reset_quotas(db_session)

    db_session.refresh(quota)
    assert quota.used == 0
    # Should be approximately 30 days from now (within a 5-second window)
    expected = now + timedelta(days=30)
    assert abs((quota.reset_at - expected).total_seconds()) < 5


def test_reset_quotas_on_empty_table_does_nothing(db_session):
    """reset_quotas with no rows in DB completes without error."""
    reset_quotas(db_session)  # must not raise


def test_multiple_expired_quotas_all_reset(db_session, test_teacher):
    """All expired quotas across multiple types are reset in a single call."""
    from app.db.models.quota import Quota

    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=2)

    quotas = [
        Quota(
            id=uuid.uuid4(),
            teacher_id=test_teacher.id,
            quota_type="daily_answer",
            used=50,
            limit=100,
            period="daily",
            reset_at=past,
        ),
        Quota(
            id=uuid.uuid4(),
            teacher_id=test_teacher.id,
            quota_type="monthly_session",
            used=20,
            limit=30,
            period="monthly",
            reset_at=past,
        ),
    ]
    for q in quotas:
        db_session.add(q)
    db_session.commit()

    reset_quotas(db_session)

    for q in quotas:
        db_session.refresh(q)
        assert q.used == 0


# ---------------------------------------------------------------------------
# cleanup_expired_tokens behaviour
# ---------------------------------------------------------------------------


def test_expired_token_without_refresh_token_is_deleted(db_session, test_teacher):
    """Expired token with no refresh_token is removed — it cannot be renewed."""
    from app.db.models.youtube_token import YouTubeToken

    now = datetime.now(timezone.utc)
    token = YouTubeToken(
        id=uuid.uuid4(),
        teacher_id=test_teacher.id,
        access_token="encrypted_token_data",
        refresh_token=None,
        token_type="Bearer",
        scope="https://www.googleapis.com/auth/youtube",
        expires_at=now - timedelta(hours=1),
    )
    db_session.add(token)
    db_session.commit()

    cleanup_expired_tokens(db_session)

    result = db_session.query(YouTubeToken).filter(YouTubeToken.teacher_id == test_teacher.id).first()
    assert result is None


def test_expired_token_with_refresh_token_is_kept(db_session, test_teacher):
    """Expired token that HAS a refresh_token is preserved — the app can renew it."""
    from app.db.models.youtube_token import YouTubeToken

    now = datetime.now(timezone.utc)
    token = YouTubeToken(
        id=uuid.uuid4(),
        teacher_id=test_teacher.id,
        access_token="encrypted_token_data",
        refresh_token="refresh_token_value",
        token_type="Bearer",
        scope="https://www.googleapis.com/auth/youtube",
        expires_at=now - timedelta(hours=1),
    )
    db_session.add(token)
    db_session.commit()

    cleanup_expired_tokens(db_session)

    result = db_session.query(YouTubeToken).filter(YouTubeToken.teacher_id == test_teacher.id).first()
    assert result is not None


def test_valid_non_expired_token_is_never_deleted(db_session, test_teacher):
    """A token that has not yet expired is left alone regardless of refresh_token."""
    from app.db.models.youtube_token import YouTubeToken

    now = datetime.now(timezone.utc)
    token = YouTubeToken(
        id=uuid.uuid4(),
        teacher_id=test_teacher.id,
        access_token="encrypted_token_data",
        refresh_token=None,
        token_type="Bearer",
        scope="https://www.googleapis.com/auth/youtube",
        expires_at=now + timedelta(hours=1),
    )
    db_session.add(token)
    db_session.commit()

    cleanup_expired_tokens(db_session)

    result = db_session.query(YouTubeToken).filter(YouTubeToken.teacher_id == test_teacher.id).first()
    assert result is not None


def test_cleanup_on_empty_table_does_nothing(db_session):
    """cleanup_expired_tokens with no rows completes without error."""
    cleanup_expired_tokens(db_session)  # must not raise
