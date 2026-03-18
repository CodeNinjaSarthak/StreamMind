# Prometheus Metrics

> Purpose: All Prometheus metrics exported by the system — name, type, labels, and example PromQL queries.

<!-- Populate from: backend/app/core/metrics.py -->
<!-- This is the SINGLE source of truth for metric definitions. -->

## Exposition

Metrics are exposed at: `GET /metrics` (Prometheus text format)

## Metrics Reference

### 1. `http_requests_total`
- **Type:** Counter
- **Labels:** `method`, `path`, `status_code`
- **Description:** Total HTTP requests handled by the FastAPI backend
- **PromQL:** `rate(http_requests_total[5m])`

---

### 2. `http_request_duration_seconds`
- **Type:** Histogram
- **Labels:** `method`, `path`
- **Description:** HTTP request latency in seconds
- **PromQL:** `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`

---

### 3. `websocket_connections_active`
- **Type:** Gauge (multiprocess liveall mode)
- **Labels:** `session_id`
- **Description:** Currently active WebSocket connections per session
- **PromQL:** `sum(websocket_connections_active)`

---

### 4. `websocket_messages_total`
- **Type:** Counter
- **Labels:** `type`, `direction`
- **Description:** Total WebSocket messages sent/received
- **PromQL:** `rate(websocket_messages_total[5m])`

---

### 5. `queue_size`
- **Type:** Gauge (multiprocess liveall mode)
- **Labels:** `queue_name`
- **Description:** Current number of items in each Redis queue
- **PromQL:** `queue_size{queue_name="classification"}`

---

### 6. `queue_processed_total`
- **Type:** Counter
- **Labels:** `queue_name`, `status`
- **Description:** Total items processed per queue (success/failure)
- **PromQL:** `rate(queue_processed_total{status="success"}[5m])`

---

### 7. `database_queries_total`
- **Type:** Counter
- **Labels:** `operation`, `table`
- **Description:** Total database queries by operation type and table
- **PromQL:** `rate(database_queries_total[5m])`

---

### 8. `database_query_duration_seconds`
- **Type:** Histogram
- **Labels:** `operation`, `table`
- **Description:** Database query latency in seconds
- **PromQL:** `histogram_quantile(0.95, rate(database_query_duration_seconds_bucket[5m]))`

---

### 9. `redis_operations_total`
- **Type:** Counter
- **Labels:** `operation`
- **Description:** Total Redis operations
- **PromQL:** `rate(redis_operations_total[5m])`

---

### 10. `worker_heartbeat`
- **Type:** Gauge (multiprocess liveall mode)
- **Labels:** `worker_name`
- **Description:** Last heartbeat timestamp per worker
- **PromQL:** `time() - worker_heartbeat`

---

### 11. `quota_usage` / `quota_limit`
- **Type:** Gauge (multiprocess liveall mode)
- **Labels:** `teacher_id`, `quota_type`
- **Description:** Current quota usage and limits per teacher
- **PromQL:** `quota_usage / quota_limit`

## Worker Queue Metrics

Workers export additional metrics via `workers/common/metrics.py`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `worker_items_processed_total` | Counter | `worker_name` | Items processed per worker |
| `worker_processing_duration_seconds` | Histogram | `worker_name` | Processing time per item |
| `worker_errors_total` | Counter | `worker_name` | Errors per worker |
| `gemini_circuit_state` | Gauge | `worker_name` | Circuit breaker state (0=closed, 1=half_open, 2=open) |

Queue depths are updated by `update_queue_depths()` which polls all 6 queues and updates the `queue_depth` gauge.

## Alerting Rules

Alerting thresholds that use these metrics are defined in:
[observability/alerting.md](alerting.md)

Do not duplicate metric definitions there.
