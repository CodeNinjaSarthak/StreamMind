# Answer Generation Worker

> Purpose: AnswerGenerationPayload → RAG + LLM → Answer record (is_posted=False) → enqueue to youtube_posting.

<!-- Populate from: workers/answer_generation/worker.py, workers/common/schemas.py -->

## Input Payload

`AnswerGenerationPayload` (from `workers/common/schemas.py`):

```json
{
  "cluster_id": "uuid",
  "session_id": "uuid",
  "question_texts": ["string", "..."]
}
```

## Processing

1. Load cluster's representative question text
2. RAG retrieval: query pgvector document store for relevant chunks (top-K by cosine similarity)
3. Build LLM prompt: question + retrieved context
4. Call `GeminiClient.generate_answer(prompt)`
5. Create `Answer` record with `is_posted=False`
6. Emit WebSocket event to notify teacher dashboard (new answer available for review)
7. Enqueue `YouTubePostingPayload` to `QUEUE_YOUTUBE_POSTING` (pending teacher approval)

## RAG Retrieval

- Retrieves top 5 nearest RAG documents by centroid embedding (cosine distance)
- Documents are scoped to the teacher who owns the session (teacher_id filter)
- Two-prompt system: with-context prompt when documents exist, without-context when none available
- Answer is moderated via ModerationService before saving

## Answer Record

| Field | Value |
|-------|-------|
| `Answer.cluster_id` | FK to cluster |
| `Answer.text` | Generated answer text |
| `Answer.is_posted` | `False` (pending approval) |
| `Answer.posted_at` | `null` (set when posted) |

For field definitions see [data/schema.md](../data/schema.md).

## Teacher Approval Flow

After this worker creates the `Answer` record:
1. WebSocket event notifies the teacher dashboard
2. Teacher reviews, optionally edits, then approves via `POST /api/v1/dashboard/answers/{answer_id}/approve`
3. youtube_posting worker posts the approved answer

See [ADR-004](../architecture/decisions/ADR-004-rag-design.md) for the rationale.

## Output

Enqueues to `QUEUE_YOUTUBE_POSTING`. See [workers/youtube-posting.md](youtube-posting.md).
For the WebSocket event emitted, see [api/websocket-events.md](../api/websocket-events.md).
