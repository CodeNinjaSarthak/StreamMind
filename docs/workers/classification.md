# Classification Worker

> Purpose: ClassificationPayload → is_question + confidence_score → enqueue to embedding queue.

<!-- Populate from: workers/classification/worker.py, workers/common/schemas.py -->

## Input Payload

`ClassificationPayload` (from `workers/common/schemas.py`):

```json
{
  "comment_id": "uuid",
  "session_id": "uuid",
  "text": "string"
}
```

## Processing

1. Call `GeminiClient.classify_question(text)`
2. Update `Comment` record: `is_question`, `confidence_score`
3. If `is_question=True`: enqueue `EmbeddingPayload` to `QUEUE_EMBEDDING`
4. If `is_question=False`: no further processing
5. Publish `comment_classified` WebSocket event via Redis pub/sub

## Output (on is_question=True)

Enqueues to `QUEUE_EMBEDDING`. See [workers/embeddings.md](embeddings.md).

## Gemini Prompt

<!-- What prompt is sent to Gemini? What response format is expected? -->

## Error Handling

<!-- What happens if Gemini call fails? Retry behavior? -->
See [workers/overview.md](overview.md) for retry policy.

## Circuit Breaker

The classification worker implements a circuit breaker pattern for Gemini API calls:
- **Closed** (normal): calls proceed
- **Open** (failing): calls skipped, task retried later
- **Half-open** (probing): single call attempted to test recovery

State exported as Prometheus gauge: `gemini_circuit_state{worker_name="classification"}`

## DB Updates

| Field | Value |
|-------|-------|
| `Comment.is_question` | `True` / `False` |
| `Comment.confidence_score` | float 0.0–1.0 |

For field definitions see [data/schema.md](../data/schema.md).
