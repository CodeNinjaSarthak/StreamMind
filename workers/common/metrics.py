"""Prometheus metrics for workers."""

from workers.common.prometheus_setup import setup_multiproc_dir

setup_multiproc_dir()

from prometheus_client import (  # noqa: E402
    Counter,
    Gauge,
    Histogram,
)

from workers.common.queue import (  # noqa: E402
    QUEUE_ANSWER_GENERATION,
    QUEUE_CLASSIFICATION,
    QUEUE_CLUSTERING,
    QUEUE_COMMENT_INGEST,
    QUEUE_EMBEDDING,
    QUEUE_YOUTUBE_POSTING,
)

ALL_QUEUES = [
    QUEUE_COMMENT_INGEST,
    QUEUE_CLASSIFICATION,
    QUEUE_EMBEDDING,
    QUEUE_CLUSTERING,
    QUEUE_ANSWER_GENERATION,
    QUEUE_YOUTUBE_POSTING,
]

worker_items_processed_total = Counter(
    "worker_items_processed_total",
    "Total items processed by workers",
    ["worker_name"],
)

worker_processing_duration_seconds = Histogram(
    "worker_processing_duration_seconds",
    "Time spent processing a single item",
    ["worker_name"],
)

worker_errors_total = Counter(
    "worker_errors_total",
    "Total worker errors",
    ["worker_name"],
)

queue_depth = Gauge(
    "queue_depth",
    "Current number of items in queue",
    ["queue_name"],
    multiprocess_mode="liveall",
)

gemini_circuit_state = Gauge(
    "gemini_circuit_state",
    "Gemini circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["worker_name"],
    multiprocess_mode="liveall",
)


def record_processing(worker_name, duration, success):
    """Record a processed item with timing.

    Args:
        worker_name: Name of the worker.
        duration: Processing duration in seconds.
        success: Whether processing succeeded.
    """
    worker_items_processed_total.labels(worker_name=worker_name).inc()
    worker_processing_duration_seconds.labels(worker_name=worker_name).observe(duration)
    if not success:
        worker_errors_total.labels(worker_name=worker_name).inc()


def update_queue_depths(queue_manager):
    """Poll Redis ZCARD for each queue and update the queue_depth gauge.

    Args:
        queue_manager: QueueManager instance with a size() method.
    """
    for q in ALL_QUEUES:
        queue_depth.labels(queue_name=q).set(queue_manager.size(q))
