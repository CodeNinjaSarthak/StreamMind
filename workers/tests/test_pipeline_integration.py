"""Pipeline integration tests.

Tests the end-to-end CONTRACT: a comment that enters a pipeline stage
produces the expected output in the downstream queue and DB state.

Gemini is the ONLY thing mocked — everything else is real
(fakeredis + test DB). Each test calls the extracted process_task()
directly, never the polling loop.
"""

import pytest
from app.services.gemini.circuit_breaker import (
    CircuitOpenError,
    GeminiCircuitBreaker,
)

from workers.common.queue import (
    QUEUE_CLUSTERING,
    QUEUE_EMBEDDING,
)

# ---------------------------------------------------------------------------
# Classification stage
# ---------------------------------------------------------------------------


def test_question_comment_reaches_embedding_queue(queue_manager, db_session, gemini_mock, test_comment, monkeypatch):
    """Classification forwards confirmed questions to embedding queue."""
    gemini_mock.classify_question.return_value = {"is_question": True, "confidence": 0.95}

    monkeypatch.setattr("workers.classification.worker.QueueManager", lambda: queue_manager)

    from workers.classification.worker import process_task

    task = {"comment_id": str(test_comment.id), "text": test_comment.text}
    process_task(task, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_EMBEDDING) == 1
    db_session.refresh(test_comment)
    assert test_comment.is_question is True


def test_non_question_comment_is_dropped(queue_manager, db_session, gemini_mock, test_comment):
    """Non-question classification does not forward to embedding queue."""
    gemini_mock.classify_question.return_value = {"is_question": False, "confidence": 0.90}

    from workers.classification.worker import process_task

    task = {"comment_id": str(test_comment.id), "text": test_comment.text}
    process_task(task, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_EMBEDDING) == 0
    db_session.refresh(test_comment)
    assert test_comment.is_question is False


def test_classification_gemini_failure_raises(queue_manager, db_session, gemini_mock, test_comment):
    """Gemini failure during classification propagates as exception.

    The caller (main loop) is responsible for retry/DLQ — process_task
    must not swallow the error.
    """
    gemini_mock.classify_question.side_effect = RuntimeError("Gemini unavailable")

    from workers.classification.worker import process_task

    task = {"comment_id": str(test_comment.id), "text": test_comment.text}
    with pytest.raises(RuntimeError, match="Gemini unavailable"):
        process_task(task, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_EMBEDDING) == 0


def test_open_circuit_fails_fast_without_calling_gemini(queue_manager, db_session, gemini_mock, test_comment):
    """Open circuit breaker prevents Gemini calls entirely."""
    # Replace the mock's classify_question so it checks the circuit breaker first,
    # matching real GeminiClient behavior
    real_cb = GeminiCircuitBreaker(failure_threshold=3, recovery_timeout=30.0)
    for _ in range(3):
        real_cb.record_failure()

    def classify_with_circuit_breaker(text):
        real_cb.ensure_closed()
        return gemini_mock.classify_question.return_value

    gemini_mock.classify_question.side_effect = classify_with_circuit_breaker

    from workers.classification.worker import process_task

    task = {"comment_id": str(test_comment.id), "text": test_comment.text}
    with pytest.raises(CircuitOpenError):
        process_task(task, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_EMBEDDING) == 0


# ---------------------------------------------------------------------------
# Embeddings stage
# ---------------------------------------------------------------------------


def test_embedded_comment_reaches_clustering_queue(queue_manager, db_session, gemini_mock, test_comment):
    """Embedding stage forwards embedded comments to clustering queue."""
    embedding = [0.1] * 768
    gemini_mock.generate_embedding.return_value = embedding

    from workers.embeddings.worker import process_task

    task = {"comment_id": str(test_comment.id), "text": test_comment.text}
    process_task(task, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_CLUSTERING) == 1
    db_session.refresh(test_comment)
    assert test_comment.embedding is not None


def test_embeddings_gemini_failure_raises(queue_manager, db_session, gemini_mock, test_comment):
    """Gemini failure during embedding propagates as exception."""
    gemini_mock.generate_embedding.side_effect = RuntimeError("Gemini unavailable")

    from workers.embeddings.worker import process_task

    task = {"comment_id": str(test_comment.id), "text": test_comment.text}
    with pytest.raises(RuntimeError, match="Gemini unavailable"):
        process_task(task, gemini_mock, queue_manager, db_session, None)

    assert queue_manager.size(QUEUE_CLUSTERING) == 0
