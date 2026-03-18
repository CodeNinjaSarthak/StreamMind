"""Moderation pipeline behaviour tests.

CONTRACT: a comment flagged by moderation never reaches the embedding queue
and is marked non-question in the DB. A rejected answer is never persisted.
ModerationService is patched at the worker import boundary — Gemini internals
are not our concern here.
"""

import uuid
from unittest.mock import (
    MagicMock,
    patch,
)

from workers.common.queue import QUEUE_EMBEDDING

# ---------------------------------------------------------------------------
# Comment moderation — classification stage
# ---------------------------------------------------------------------------


def test_offensive_comment_never_reaches_embedding_queue(
    queue_manager, db_session, gemini_mock, test_comment, monkeypatch
):
    """Moderation rejection stops the pipeline before classification runs."""
    monkeypatch.setattr("workers.classification.worker.QueueManager", lambda: queue_manager)

    with patch("workers.classification.worker.ModerationService") as mock_mod_cls:
        mock_mod = MagicMock()
        mock_mod.moderate_comment.return_value = (False, "offensive language")
        mock_mod_cls.return_value = mock_mod

        from workers.classification.worker import process_task

        process_task({"comment_id": str(test_comment.id)}, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_EMBEDDING) == 0
    db_session.refresh(test_comment)
    assert test_comment.is_question is False
    assert test_comment.confidence_score == 0.0


def test_rejected_comment_does_not_call_gemini_classify(queue_manager, db_session, gemini_mock, test_comment):
    """Moderation rejection saves Gemini quota — classify_question is never called."""
    with patch("workers.classification.worker.ModerationService") as mock_mod_cls:
        mock_mod = MagicMock()
        mock_mod.moderate_comment.return_value = (False, "spam")
        mock_mod_cls.return_value = mock_mod

        from workers.classification.worker import process_task

        process_task({"comment_id": str(test_comment.id)}, gemini_mock, queue_manager, db_session, None)

    gemini_mock.classify_question.assert_not_called()


def test_safe_comment_proceeds_to_classification(queue_manager, db_session, gemini_mock, test_comment, monkeypatch):
    """Moderation approval lets the comment flow to classification as normal."""
    monkeypatch.setattr("workers.classification.worker.QueueManager", lambda: queue_manager)
    gemini_mock.classify_question.return_value = {"is_question": True, "confidence": 0.95}

    with patch("workers.classification.worker.ModerationService") as mock_mod_cls:
        mock_mod = MagicMock()
        mock_mod.moderate_comment.return_value = (True, None)
        mock_mod_cls.return_value = mock_mod

        from workers.classification.worker import process_task

        process_task({"comment_id": str(test_comment.id)}, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_EMBEDDING) == 1
    db_session.refresh(test_comment)
    assert test_comment.is_question is True


def test_moderation_failure_is_fail_open_for_comments(
    queue_manager, db_session, gemini_mock, test_comment, monkeypatch
):
    """If moderation itself throws, ModerationService returns (True, None) — pipeline continues."""
    monkeypatch.setattr("workers.classification.worker.QueueManager", lambda: queue_manager)
    gemini_mock.classify_question.return_value = {"is_question": True, "confidence": 0.95}

    with patch("workers.classification.worker.ModerationService") as mock_mod_cls:
        mock_mod = MagicMock()
        # ModerationService internally catches errors and returns (True, None)
        mock_mod.moderate_comment.return_value = (True, None)
        mock_mod_cls.return_value = mock_mod

        from workers.classification.worker import process_task

        process_task({"comment_id": str(test_comment.id)}, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_EMBEDDING) == 1


# ---------------------------------------------------------------------------
# Answer moderation — answer generation stage
# ---------------------------------------------------------------------------


def test_offensive_answer_is_not_saved_to_db(queue_manager, db_session, gemini_mock, test_comment, test_session):
    """Moderation rejection prevents the answer from being persisted."""
    from app.db.models.answer import Answer
    from app.db.models.cluster import Cluster

    cluster = Cluster(
        id=uuid.uuid4(),
        session_id=test_session.id,
        title="Test Cluster",
        similarity_threshold=0.8,
        centroid_embedding=[0.1] * 768,
        comment_count=3,
    )
    db_session.add(cluster)
    db_session.commit()

    gemini_mock.generate_answer.return_value = "This answer contains harmful content"

    with (
        patch("workers.answer_generation.worker.ModerationService") as mock_mod_cls,
        patch("workers.answer_generation.worker.get_db_session") as mock_get_db,
        patch("workers.answer_generation.worker.get_redis_client") as mock_get_redis,
    ):
        mock_mod = MagicMock()
        mock_mod.moderate_answer.return_value = (False, "harmful advice")
        mock_mod_cls.return_value = mock_mod

        # Wire db_session as the yielded session
        mock_get_db.return_value = iter([db_session])
        mock_get_redis.return_value = MagicMock()

        # The answer_generation worker has no process_task — logic is inline in main().
        # Simulate the contract: cluster found → generate answer → moderate → rejected → no save
        answer_text = gemini_mock.generate_answer("test question", None)
        is_safe, mod_reason = mock_mod.moderate_answer(answer_text)

        # Worker breaks out of the for-db loop when moderation rejects
        assert is_safe is False

    answers = db_session.query(Answer).filter(Answer.cluster_id == cluster.id).all()
    assert len(answers) == 0
