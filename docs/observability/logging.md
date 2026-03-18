# Logging

> Purpose: Log levels, LOG_JSON structured format, RequestContextMiddleware, and request_id propagation.

<!-- Populate from: backend/app/middleware/, backend/app/core/logging.py (verify path) -->

## Log Levels

| Level | When |
|-------|------|
| `DEBUG` | Detailed flow (disabled in production) |
| `INFO` | Normal operations: request received, task processed |
| `WARNING` | Recoverable issues: retry attempt, quota approaching limit |
| `ERROR` | Failures requiring attention: worker crash, API error |
| `CRITICAL` | System-level failures: DB down, Redis unreachable |

Configure via `LOG_LEVEL` env var. See [infra/configuration-reference.md](../infra/configuration-reference.md).

## JSON Format

When `LOG_JSON=true`, logs are emitted as structured JSON:

```json
{
  "timestamp": "2026-03-01T12:00:00Z",
  "level": "INFO",
  "request_id": "uuid",
  "message": "Request processed",
  "path": "/api/v1/sessions",
  "method": "GET",
  "status_code": 200,
  "duration_ms": 45
}
```

Enable via `LOG_JSON=true` env var (recommended in production).

## RequestContextMiddleware

`backend/app/core/middleware.py`

- Assigns a unique `request_id` (UUID) to each incoming HTTP request
- Injects `request_id` into log context for the duration of the request
- Returns `X-Request-ID` response header
- Returns `X-Process-Time` response header (request duration)
- Workers inherit a `task_id` for equivalent correlation

## Worker Logging

Workers log with a `task_id` field corresponding to the queue payload ID, enabling
end-to-end tracing of a comment through the pipeline:

```
comment_id=abc123 → classification task_id=xyz → embedding task_id=def → ...
```

## Log Aggregation

<!-- Document log shipping: stdout → log aggregator (CloudWatch, Loki, etc.) -->
