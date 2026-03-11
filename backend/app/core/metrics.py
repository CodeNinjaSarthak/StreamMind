"""Prometheus metrics for observability."""

from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

http_requests_total = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "endpoint"]
)

websocket_connections_active = Gauge(
    "websocket_connections_active", "Number of active WebSocket connections", ["session_id"]
)

websocket_messages_total = Counter("websocket_messages_total", "Total WebSocket messages", ["type", "direction"])

database_queries_total = Counter("database_queries_total", "Total database queries", ["operation", "table"])

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds", "Database query duration in seconds", ["operation", "table"]
)

redis_operations_total = Counter("redis_operations_total", "Total Redis operations", ["operation"])

queue_size = Gauge("queue_size", "Number of items in queue", ["queue_name"])

queue_processed_total = Counter("queue_processed_total", "Total queue items processed", ["queue_name", "status"])

worker_heartbeat = Gauge("worker_heartbeat", "Worker last heartbeat timestamp", ["worker_name"])

quota_usage = Gauge("quota_usage", "Quota usage", ["teacher_id", "quota_type"])

quota_limit = Gauge("quota_limit", "Quota limit", ["teacher_id", "quota_type"])


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics endpoint.

    Args:
        request: Incoming request.

    Returns:
        Metrics response.
    """
    if not settings.enable_metrics:
        return Response("Metrics disabled", status_code=404)

    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


def increment_http_requests(method: str, endpoint: str, status: int) -> None:
    """Increment HTTP request counter.

    Args:
        method: HTTP method.
        endpoint: Request endpoint.
        status: Response status code.
    """
    if settings.enable_metrics:
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()


def observe_request_duration(method: str, endpoint: str, duration: float) -> None:
    """Record HTTP request duration.

    Args:
        method: HTTP method.
        endpoint: Request endpoint.
        duration: Request duration in seconds.
    """
    if settings.enable_metrics:
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)


def set_websocket_connections(session_id: str, count: int) -> None:
    """Set active WebSocket connection count.

    Args:
        session_id: Session identifier.
        count: Number of connections.
    """
    if settings.enable_metrics:
        websocket_connections_active.labels(session_id=session_id).set(count)


def increment_websocket_messages(msg_type: str, direction: str) -> None:
    """Increment WebSocket message counter.

    Args:
        msg_type: Message type.
        direction: Message direction (inbound/outbound).
    """
    if settings.enable_metrics:
        websocket_messages_total.labels(type=msg_type, direction=direction).inc()


def set_queue_size(queue_name: str, size: int) -> None:
    """Set queue size gauge.

    Args:
        queue_name: Queue name.
        size: Queue size.
    """
    if settings.enable_metrics:
        queue_size.labels(queue_name=queue_name).set(size)


def increment_queue_processed(queue_name: str, status: str) -> None:
    """Increment queue processed counter.

    Args:
        queue_name: Queue name.
        status: Processing status (success/failure).
    """
    if settings.enable_metrics:
        queue_processed_total.labels(queue_name=queue_name, status=status).inc()
