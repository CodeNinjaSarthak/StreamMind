# YouTube Posting Worker

> Purpose: YouTubePostingPayload → YouTube API → is_posted=True → answer_posted WebSocket event.

<!-- Populate from: workers/youtube_posting/worker.py, workers/common/schemas.py -->

## Input Payload

`YouTubePostingPayload` (from `workers/common/schemas.py`):

```json
{
  "answer_id": "uuid",
  "session_id": "uuid"
}
```

## Processing

1. Fetch Answer, StreamingSession, and YouTubeToken from DB
2. Check YouTube quota before posting (costs 50 units)
3. Get `live_chat_id` from Redis cache (set by youtube_polling worker); retry if not cached
4. Call `YouTubeClient.post_message(chat_id, answer_text)`
3. Update `Answer.is_posted = True`
4. Emit `answer_posted` WebSocket event to session

For the exact WebSocket event payload, see [api/websocket-events.md](../api/websocket-events.md).

## Quota Cost

Each post costs **50 YouTube API quota units**.
See [data/quota-model.md](../data/quota-model.md) — do not duplicate the quota table here.

## chat_id Source

The `chat_id` is cached in Redis by the youtube_polling worker.
Redis key pattern: `youtube:poll:{session_id}:chat_id` (TTL: 3600s)

## Error Handling

- On 403 quota exceeded: mark answer as failed, do not retry, alert teacher
- On network error: retry per standard backoff policy
  See [workers/overview.md](overview.md) for retry details.

## DB Updates

| Field | Value |
|-------|-------|
| `Answer.is_posted` | `True` |
| `Answer.posted_at` | timestamp |

For field definitions see [data/schema.md](../data/schema.md).
