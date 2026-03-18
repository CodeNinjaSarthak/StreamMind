# Workers Overview

> Purpose: QueueManager mechanics, priority, exponential backoff, DLQ, and runner.py.

<!-- Populate from: workers/common/queue.py, workers/runner.py -->

## Architecture

Workers are independent Python processes that:
1. Pull tasks from Redis sorted-set queues via `QueueManager.dequeue()`
2. Process the task (call Gemini, update DB, etc.)
3. On success: enqueue next task in the pipeline
4. On failure: retry with exponential backoff; move to DLQ after max retries

See [architecture/data-flow.md](../architecture/data-flow.md) for how workers fit into
the 9-step pipeline.

## QueueManager

`workers/common/queue.py`

| Method | Description |
|--------|-------------|
| `enqueue(queue, payload, priority)` | Add task to sorted set (score = timestamp - priority offset) |
| `dequeue(queue)` | Atomic pop of highest-priority task |
| `retry(queue, payload, attempt)` | Re-enqueue with backoff delay |
| `move_to_dlq(queue, payload)` | Move to `{queue}:dlq` after max retries |

## Queue Constants

| Constant | Queue Name | Description |
|----------|-----------|-------------|
| `QUEUE_CLASSIFICATION` | `classification` | Raw comments awaiting classification |
| `QUEUE_EMBEDDING` | `embedding` | Classified questions awaiting embedding |
| `QUEUE_CLUSTERING` | `clustering` | Embedded comments awaiting clustering |
| `QUEUE_ANSWER_GENERATION` | `answer_generation` | Clusters awaiting answer generation |
| `QUEUE_YOUTUBE_POSTING` | `youtube_posting` | Approved answers awaiting YouTube post |

## Retry Policy

Exponential backoff with jitter:
- Attempt 1: 1s delay
- Attempt 2: 2s delay
- Attempt 3: 4s delay
- After max retries: moved to DLQ (`{queue}:dlq`)

## Dead Letter Queue (DLQ)

Failed tasks accumulate in `{queue}:dlq` sorted sets. Inspect with:

```bash
redis-cli ZRANGE classification:dlq 0 -1
```

See [state/runbooks/worker-crash.md](../state/runbooks/worker-crash.md) for DLQ review procedure.

## runner.py

> **Stub**: `workers/runner.py` is not implemented. `make run-workers` calls it but
> it does nothing useful. Use `./start_dev.sh` instead, which launches all workers
> via tmux.

### start_dev.sh Workers

`./start_dev.sh` starts 9 processes in a tmux session:

| Pane | Process |
|------|---------|
| 0 | Backend (uvicorn) |
| 1 | Classification worker |
| 2 | Embeddings worker |
| 3 | Clustering worker |
| 4 | Answer generation worker |
| 5 | YouTube polling worker |
| 6 | YouTube posting worker |
| 7 | Scheduler (APScheduler — quota reset + token cleanup) |
| 8 | Frontend (Vite dev server) |

## Priority

<!-- How priority scores work in sorted sets; use cases for high-priority tasks -->
