"""Queue management for worker tasks."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import redis

from workers.common.redis import get_redis_client

logger = logging.getLogger(__name__)

QUEUE_COMMENT_INGEST = "comment_ingest"
QUEUE_CLASSIFICATION = "classification"
QUEUE_EMBEDDING = "embedding"
QUEUE_CLUSTERING = "clustering"
QUEUE_ANSWER_GENERATION = "answer_generation"

DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 60
DLQ_SUFFIX = "_dlq"


class QueuePayload:
    """Base class for queue payloads."""

    def __init__(
        self,
        task_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
        retry_count: int = 0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        **kwargs
    ):
        """Initialize queue payload.

        Args:
            task_id: Unique task identifier.
            created_at: Task creation timestamp.
            retry_count: Current retry count.
            max_retries: Maximum retry attempts.
            **kwargs: Additional payload data.
        """
        self.task_id = task_id or str(uuid4())
        self.created_at = created_at or datetime.now(timezone.utc)
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.data = kwargs

    def to_dict(self) -> Dict[str, Any]:
        """Convert payload to dictionary.

        Returns:
            Dictionary representation of payload.
        """
        return {
            "task_id": self.task_id,
            "created_at": self.created_at.isoformat(),
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            **self.data
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueuePayload":
        """Create payload from dictionary.

        Args:
            data: Dictionary data.

        Returns:
            QueuePayload instance.
        """
        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            task_id=data.get("task_id"),
            created_at=created_at,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", DEFAULT_MAX_RETRIES),
            **{k: v for k, v in data.items() if k not in ["task_id", "created_at", "retry_count", "max_retries"]}
        )


class QueueManager:
    """Manager for Redis-based queues."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize queue manager.

        Args:
            redis_client: Optional Redis client instance.
        """
        self.redis_client = redis_client or get_redis_client()

    def enqueue(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        priority: int = 0
    ) -> bool:
        """Add task to queue.

        Args:
            queue_name: Name of the queue.
            payload: Task payload dictionary.
            priority: Task priority (lower number = higher priority).

        Returns:
            True if successfully enqueued.
        """
        try:
            task_data = json.dumps(payload)
            score = priority * 1000000 + time.time()
            self.redis_client.zadd(queue_name, {task_data: score})
            logger.info(f"Enqueued task to {queue_name}", extra={"task_id": payload.get("task_id")})
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue task to {queue_name}: {e}")
            return False

    def dequeue(
        self,
        queue_name: str,
        timeout: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Remove and return task from queue.

        Args:
            queue_name: Name of the queue.
            timeout: Block timeout in seconds (0 = no block).

        Returns:
            Task payload dictionary or None.
        """
        try:
            result = self.redis_client.zpopmin(queue_name, count=1)
            if not result:
                return None

            task_data, _ = result[0]
            payload = json.loads(task_data)
            logger.info(f"Dequeued task from {queue_name}", extra={"task_id": payload.get("task_id")})
            return payload
        except Exception as e:
            logger.error(f"Failed to dequeue task from {queue_name}: {e}")
            return None

    def peek(self, queue_name: str, count: int = 1) -> list[Dict[str, Any]]:
        """Peek at tasks without removing them.

        Args:
            queue_name: Name of the queue.
            count: Number of tasks to peek.

        Returns:
            List of task payload dictionaries.
        """
        try:
            results = self.redis_client.zrange(queue_name, 0, count - 1)
            return [json.loads(task_data) for task_data in results]
        except Exception as e:
            logger.error(f"Failed to peek queue {queue_name}: {e}")
            return []

    def size(self, queue_name: str) -> int:
        """Get queue size.

        Args:
            queue_name: Name of the queue.

        Returns:
            Number of tasks in queue.
        """
        try:
            return self.redis_client.zcard(queue_name)
        except Exception as e:
            logger.error(f"Failed to get size of queue {queue_name}: {e}")
            return 0

    def retry(
        self,
        queue_name: str,
        payload: Dict[str, Any],
        delay: int = DEFAULT_RETRY_DELAY
    ) -> bool:
        """Retry a failed task.

        Args:
            queue_name: Name of the queue.
            payload: Task payload.
            delay: Delay before retry in seconds.

        Returns:
            True if task requeued, False if moved to DLQ.
        """
        retry_count = payload.get("retry_count", 0)
        max_retries = payload.get("max_retries", DEFAULT_MAX_RETRIES)

        if retry_count >= max_retries:
            logger.warning(
                f"Task exceeded max retries, moving to DLQ",
                extra={"task_id": payload.get("task_id"), "queue": queue_name}
            )
            return self.move_to_dlq(queue_name, payload)

        payload["retry_count"] = retry_count + 1
        score = time.time() + delay

        try:
            task_data = json.dumps(payload)
            self.redis_client.zadd(queue_name, {task_data: score})
            logger.info(
                f"Task requeued for retry",
                extra={
                    "task_id": payload.get("task_id"),
                    "queue": queue_name,
                    "retry_count": payload["retry_count"]
                }
            )
            return True
        except Exception as e:
            logger.error(f"Failed to retry task: {e}")
            return False

    def move_to_dlq(self, queue_name: str, payload: Dict[str, Any]) -> bool:
        """Move task to dead letter queue.

        Args:
            queue_name: Original queue name.
            payload: Task payload.

        Returns:
            True if successfully moved to DLQ.
        """
        dlq_name = f"{queue_name}{DLQ_SUFFIX}"
        payload["failed_at"] = datetime.now(timezone.utc).isoformat()

        try:
            task_data = json.dumps(payload)
            self.redis_client.zadd(dlq_name, {task_data: time.time()})
            logger.error(
                f"Task moved to DLQ",
                extra={"task_id": payload.get("task_id"), "dlq": dlq_name}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to move task to DLQ: {e}")
            return False

    def clear(self, queue_name: str) -> bool:
        """Clear all tasks from queue.

        Args:
            queue_name: Name of the queue.

        Returns:
            True if successfully cleared.
        """
        try:
            self.redis_client.delete(queue_name)
            logger.info(f"Queue {queue_name} cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear queue {queue_name}: {e}")
            return False


def enqueue_task(queue_name: str, payload: Dict[str, Any], priority: int = 0) -> bool:
    """Helper function to enqueue a task.

    Args:
        queue_name: Queue name.
        payload: Task payload.
        priority: Task priority.

    Returns:
        True if enqueued successfully.
    """
    manager = QueueManager()
    return manager.enqueue(queue_name, payload, priority)


def dequeue_task(queue_name: str, timeout: int = 0) -> Optional[Dict[str, Any]]:
    """Helper function to dequeue a task.

    Args:
        queue_name: Queue name.
        timeout: Block timeout.

    Returns:
        Task payload or None.
    """
    manager = QueueManager()
    return manager.dequeue(queue_name, timeout)
