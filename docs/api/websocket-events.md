# WebSocket Events

> Purpose: All event types with exact JSON payloads and the base envelope.

<!-- Populate from: backend/app/services/websocket/, workers that emit events -->
<!-- This is the SINGLE source of truth for WS event shapes. -->

## Connection

```
ws://{host}/ws/{session_id}
```

**Auth:** First message must be `{"type": "auth", "token": "<jwt>"}`.
Optional `?token=` query param also supported.
- Missing/invalid token: close code `4001`
- Session not owned by user: close code `4003`

See [api/error-codes.md](error-codes.md) for WS close codes.

## Base Envelope

All events follow this envelope:

```json
{
  "type": "event_type_string",
  "session_id": "uuid",
  "timestamp": "ISO 8601 UTC",
  "data": { ... }
}
```

## Event Types

### 1. `comment_created`
Emitted when a new comment (YouTube or manual) is ingested.

```json
{
  "type": "comment_created",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "comment_id": "uuid",
    "session_id": "uuid",
    "text": "string",
    "author": "string",
    "youtube_comment_id": "string"
  }
}
```

---

### 2. `comment_classified`
Emitted after classification worker processes a comment.

```json
{
  "type": "comment_classified",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "comment_id": "uuid",
    "is_question": true,
    "confidence_score": 0.95
  }
}
```

---

### 3. `comment_embedded`
Emitted after embeddings worker generates the comment's vector.

```json
{
  "type": "comment_embedded",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "comment_id": "uuid"
  }
}
```

---

### 4. `cluster_created`
Emitted when the clustering worker creates a new cluster.

```json
{
  "type": "cluster_created",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "id": "uuid",
    "title": "string",
    "comment_count": 1
  }
}
```

---

### 5. `cluster_updated`
Emitted when a comment joins an existing cluster.

```json
{
  "type": "cluster_updated",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "id": "uuid",
    "title": "string",
    "comment_count": 5
  }
}
```

---

### 6. `answer_ready`
Emitted when answer_generation worker creates an Answer record.

```json
{
  "type": "answer_ready",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "answer_id": "uuid",
    "cluster_id": "uuid",
    "text": "string",
    "is_posted": false
  }
}
```

---

### 7. `cluster_summary_failed`
Emitted when Gemini cluster title summarization fails.

```json
{
  "type": "cluster_summary_failed",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "cluster_id": "uuid"
  }
}
```

---

### 8. `answer_posted`
Emitted by youtube_posting worker after successfully posting to YouTube.

```json
{
  "type": "answer_posted",
  "session_id": "uuid",
  "timestamp": "...",
  "data": {
    "answer_id": "uuid",
    "cluster_id": "uuid",
    "posted_at": "ISO 8601 UTC"
  }
}
```

---

### 9. `quota_alert`
Emitted when YouTube API quota is running low.

### 10. `quota_exceeded`
Emitted when YouTube API quota is exhausted.

## Heartbeat

The WebSocket connection supports ping/pong for keep-alive. Heartbeat interval: 30 seconds (configurable via `WEBSOCKET_HEARTBEAT_INTERVAL`). Connection timeout: 300 seconds (configurable via `WEBSOCKET_TIMEOUT`).
