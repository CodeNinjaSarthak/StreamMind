"""Contract tests for QueueManager.

Tests assert ONLY on observable behavior (dequeue return values, size).
Never asserts on Redis key name strings or ZSET internals.
DLQ name is derived using the same constant as production code.
"""

from workers.common.queue import DLQ_SUFFIX


def test_enqueued_item_is_retrievable(queue_manager):
    """Items survive the enqueue → dequeue round trip."""
    payload = {"comment_id": "abc-123", "text": "test question"}
    queue_manager.enqueue("test_queue", payload)
    result = queue_manager.dequeue("test_queue")
    assert result is not None
    assert result["comment_id"] == payload["comment_id"]
    assert result["text"] == payload["text"]


def test_dequeue_empty_queue_returns_none(queue_manager):
    """Dequeuing an empty queue returns None, does not raise."""
    result = queue_manager.dequeue("empty_queue")
    assert result is None


def test_failed_item_is_retried(queue_manager):
    """retry() re-enqueues the item so it is available for dequeue again."""
    payload = {"comment_id": "abc-123", "retry_count": 0, "max_retries": 3}
    queue_manager.enqueue("test_queue", payload)
    task = queue_manager.dequeue("test_queue")
    queue_manager.retry("test_queue", task, delay=0)
    retried = queue_manager.dequeue("test_queue")
    assert retried is not None
    assert retried["comment_id"] == payload["comment_id"]


def test_item_moves_to_dlq_after_max_retries(queue_manager):
    """Exhausted items leave the main queue and appear in DLQ."""
    payload = {"comment_id": "abc-123", "retry_count": 3, "max_retries": 3}
    queue_manager.retry("test_queue", payload, delay=0)
    # Main queue must be empty — retry should have sent it to DLQ
    assert queue_manager.dequeue("test_queue") is None
    # DLQ must have the item
    dlq_depth = queue_manager.size(f"test_queue{DLQ_SUFFIX}")
    assert dlq_depth == 1


def test_size_reflects_queue_depth(queue_manager):
    """size() stays consistent with enqueue and dequeue operations."""
    for i in range(3):
        queue_manager.enqueue("test_queue", {"i": i})
    assert queue_manager.size("test_queue") == 3
    queue_manager.dequeue("test_queue")
    assert queue_manager.size("test_queue") == 2
