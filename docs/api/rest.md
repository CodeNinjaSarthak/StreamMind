# REST API Reference

> Purpose: Every REST endpoint — method, path, auth required, request schema, response schema, error codes.

<!-- Populate from: backend/app/api/v1/ -->
<!-- This is the SINGLE source of truth for REST schemas. Do NOT duplicate in frontend/api-client.md or backend/*.md -->

## Conventions

- Base path: `/api/v1`
- Auth: `Authorization: Bearer <access_token>` (HTTPBearer) unless noted as public
- All timestamps: ISO 8601 UTC
- All IDs: UUID v4 strings
- Error shape: see [api/error-codes.md](error-codes.md)

---

## Auth Endpoints (`/api/v1/auth`)

### POST /api/v1/auth/register
**Auth:** Public

**Request:**
```json
{
  "email": "string",
  "password": "string",
  "name": "string"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "email": "string",
  "name": "string"
}
```

---

### POST /api/v1/auth/login
**Auth:** Public

**Request:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response 200:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

### POST /api/v1/auth/refresh
**Auth:** Bearer refresh_token

**Response 200:** Same as login response

---

### GET /api/v1/auth/me
**Auth:** Required

**Response 200:** `TeacherResponse`

---

### PATCH /api/v1/auth/profile
**Auth:** Required

**Request:**
```json
{
  "name": "string"
}
```

**Response 200:** `TeacherResponse`

---

### POST /api/v1/auth/change-password
**Auth:** Required

**Request:**
```json
{
  "current_password": "string",
  "new_password": "string"
}
```

**Response 200:** `{"message": "Password changed successfully"}`

---

### POST /api/v1/auth/logout
**Auth:** Bearer access_token

**Response 200:** `{"detail": "logged out"}`

---

## Session Endpoints (`/api/v1/sessions`)

<!-- Populate: list, create, get, update, delete, activate, comments endpoints -->

### GET /api/v1/sessions
**Auth:** Required

**Response 200:** `[SessionResponse]`

---

### POST /api/v1/sessions
**Auth:** Required

**Request:**
```json
{
  "title": "string",
  "youtube_video_id": "string | null"
}
```

**Response 201:** `SessionResponse`

---

### GET /api/v1/sessions/{session_id}
**Auth:** Required (must own session)

**Response 200:** `SessionResponse`

---

### GET /api/v1/sessions/{session_id}/comments
**Auth:** Required (must own session)

**Query params:** `limit` (default: 100), `offset` (default: 0)

**Response 200:** `[CommentResponse]`

---

### PATCH /api/v1/sessions/{session_id}
**Auth:** Required (must own session)

**Request:**
```json
{
  "title": "string | null",
  "description": "string | null"
}
```

**Response 200:** `SessionResponse`

---

### POST /api/v1/sessions/{session_id}/end
**Auth:** Required (must own session)

**Response 200:** `SessionResponse`

---

### GET /api/v1/sessions/{session_id}/clusters
**Auth:** Required (must own session)

**Response 200:** `[ClusterResponse]` (includes nested answers)

---

### GET /api/v1/sessions/{session_id}/analytics
**Auth:** Required (must own session)

**Response 200:**
```json
{
  "total_questions": 0,
  "total_clusters": 0,
  "response_rate": 0.0,
  "avg_cluster_size": 0.0,
  "peak_hour": "string | null",
  "questions_over_time": [{"hour": "ISO 8601", "count": 0}],
  "top_clusters": [{"title": "string", "comment_count": 0}]
}
```

---

## Dashboard Endpoints (`/api/v1/dashboard`)

### POST /api/v1/dashboard/sessions/{session_id}/manual-question
**Auth:** Required (must own session)

Submit a manual question bypassing YouTube polling.

**Request:**
```json
{
  "text": "string"
}
```

**Response 201:** `CommentResponse`

---

### POST /api/v1/dashboard/answers/{answer_id}/approve
**Auth:** Required

**Note:** Takes `answer_id` (not `cluster_id`). See [frontend/api-client.md](../frontend/api-client.md).

**Response 200:** `AnswerResponse`

---

### PATCH /api/v1/dashboard/answers/{answer_id}
**Auth:** Required

**Request:**
```json
{
  "text": "string"
}
```

**Response 200:** `AnswerResponse`

---

### GET /api/v1/dashboard/sessions/{session_id}/stats
**Auth:** Required (must own session)

**Response 200:**
```json
{
  "total_comments": 0,
  "questions": 0,
  "answered": 0,
  "clusters": 0,
  "answers_generated": 0,
  "answers_posted": 0
}
```

---

### GET /api/v1/dashboard/clusters/{cluster_id}/representative
**Auth:** Required (must own cluster's session)

**Response 200:**
```json
{
  "comment_id": "uuid",
  "text": "string",
  "similarity": 0.95
}
```

---

## YouTube Endpoints (`/api/v1/youtube`)

<!-- Populate: auth/url, auth/callback, auth/refresh, auth/status, auth/disconnect, videos/{id}/validate -->

### GET /api/v1/youtube/auth/url
**Auth:** Required

**Response 200:**
```json
{
  "url": "string",
  "state": "string"
}
```

---

### GET /api/v1/youtube/auth/callback
**Auth:** Public (OAuth callback)

Returns HTML that postMessages to opener window.

---

### POST /api/v1/youtube/auth/refresh
**Auth:** Required

Refreshes the YouTube access token using stored refresh token.

**Response 200:** `{"status": "refreshed"}`

---

### GET /api/v1/youtube/auth/status
**Auth:** Required

**Response 200:**
```json
{
  "connected": true,
  "expires_at": "ISO 8601 | null"
}
```

---

### DELETE /api/v1/youtube/auth/disconnect
**Auth:** Required

**Response 204:** No content

---

### GET /api/v1/youtube/videos/{video_id}/validate
**Auth:** Required

**Response 200:**
```json
{
  "valid": true,
  "is_live": true,
  "title": "string"
}
```

---

## RAG Document Endpoints (`/api/v1/rag`)

### POST /api/v1/rag/documents
**Auth:** Required

Upload a PDF, DOCX, or TXT file for RAG retrieval. Multipart form data.

**Response 200:**
```json
{
  "chunks_created": 5,
  "document_ids": ["uuid", "..."]
}
```

---

### GET /api/v1/rag/documents
**Auth:** Required

**Response 200:** `[{"id": "uuid", "title": "string", "source_type": "string", "created_at": "ISO 8601"}]`

---

### DELETE /api/v1/rag/documents/{doc_id}
**Auth:** Required (must own document)

**Response 204:** No content

---

## Comment Endpoints (`/api/v1/comments`)

### GET /api/v1/comments/{comment_id}
**Auth:** Required (must own comment's session)

**Response 200:** `CommentResponse`

---

### PATCH /api/v1/comments/{comment_id}
**Auth:** Required (must own comment's session)

Marks the comment as answered (`is_answered=True`).

**Response 200:** `CommentResponse`

---

## Cluster Endpoints (`/api/v1/clusters`)

### GET /api/v1/clusters/{cluster_id}
**Auth:** Required (must own cluster's session)

**Response 200:** `ClusterResponse`

---

### GET /api/v1/clusters/{cluster_id}/comments
**Auth:** Required (must own cluster's session)

**Query params:** `limit` (default: 50)

**Response 200:** `[CommentResponse]`

---

### PATCH /api/v1/clusters/{cluster_id}
**Auth:** Required (must own cluster's session)

**Request:**
```json
{
  "title": "string | null",
  "description": "string | null"
}
```

**Response 200:** `ClusterResponse`

---

## Answer Endpoints (`/api/v1/answers`)

### POST /api/v1/answers
**Auth:** Required

**Request:**
```json
{
  "cluster_id": "uuid",
  "comment_id": "uuid | null",
  "text": "string"
}
```

**Response 201:** `AnswerResponse`

---

### GET /api/v1/answers/{answer_id}
**Auth:** Required (must own answer's session)

**Response 200:** `AnswerResponse`

---

### PATCH /api/v1/answers/{answer_id}
**Auth:** Required

**Request:**
```json
{
  "text": "string"
}
```

**Response 200:** `AnswerResponse`

---

### POST /api/v1/answers/{answer_id}/post
**Auth:** Required

Marks answer as posted (`is_posted=True`, `posted_at=now`).

**Response 200:** `AnswerResponse`

---

## Metrics Endpoint (`/api/v1/metrics`)

### GET /api/v1/metrics
**Auth:** Required

**Response 200:**
```json
{
  "active_sessions": 0,
  "questions_processed": 0,
  "answers_generated": 0
}
```

---

## WebSocket

WebSocket connection and all events are documented in:
[api/websocket-events.md](websocket-events.md)
