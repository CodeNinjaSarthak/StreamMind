# API Contracts

This document provides detailed API contract specifications for the AI Live Doubt Manager system, including request/response schemas, authentication requirements, and WebSocket event formats.

**Base URL:** `http://localhost:8000`
**API Prefix:** `/api/v1`

---

## Authentication

All endpoints requiring authentication must include a JWT access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### POST /api/v1/auth/register

Register a new teacher account.

**Request:** (`RegisterRequest` schema from `backend/app/schemas/auth.py:32-37`)
```json
{
  "email": "teacher@example.com",
  "password": "SecurePass123",
  "name": "Jane Doe"
}
```

**Validation:**
- `email`: Valid email format (EmailStr)
- `password`: Minimum 8 characters
- `name`: 1-255 characters

**Response:** `201 Created` (`TeacherResponse` schema from `backend/app/schemas/auth.py:46-56`)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "teacher@example.com",
  "name": "Jane Doe",
  "is_active": true,
  "is_verified": false
}
```

**Errors:**
- `400 Bad Request`: Email already exists
- `422 Unprocessable Entity`: Validation error (invalid email, password too short, etc.)

---

### POST /api/v1/auth/login

Authenticate and receive JWT tokens.

**Request:** (`LoginRequest` schema from `backend/app/schemas/auth.py:25-29`)
```json
{
  "email": "teacher@example.com",
  "password": "SecurePass123"
}
```

**Response:** `200 OK` (`Token` schema from `backend/app/schemas/auth.py:9-15`)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJlbWFpbCI6InRlYWNoZXJAZXhhbXBsZS5jb20iLCJleHAiOjE3MDQxMjAwMDB9.signature",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJleHAiOjE3MDQyOTAwMDB9.signature",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Token Expiry:**
- Access token: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh token: 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)

**Errors:**
- `401 Unauthorized`: Invalid email or password
- `403 Forbidden`: Account is inactive (`is_active=false`)

---

### POST /api/v1/auth/refresh

Refresh access token using refresh token.

**Request:** (`RefreshTokenRequest` schema from `backend/app/schemas/auth.py:40-42`)
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** `200 OK` (New `Token` with updated access_token)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**
- `401 Unauthorized`: Invalid or expired refresh token

---

### GET /api/v1/auth/me

Get current authenticated teacher information.

**Authentication:** Required (Bearer token)

**Response:** `200 OK` (`TeacherResponse`)
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "teacher@example.com",
  "name": "Jane Doe",
  "is_active": true,
  "is_verified": false
}
```

**Errors:**
- `401 Unauthorized`: Missing, invalid, or expired token

---

### POST /api/v1/auth/logout

Logout and invalidate current session.

**Authentication:** Required

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "Logged out successfully"
}
```

---

## YouTube Integration

**Note:** These endpoints are currently stubs awaiting YouTube OAuth implementation.

### GET /api/v1/youtube/auth-url

Get YouTube OAuth authorization URL.

**Authentication:** Required

**Response:** `200 OK` (To be implemented)
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=..."
}
```

---

### POST /api/v1/youtube/auth

Exchange OAuth authorization code for access tokens.

**Authentication:** Required

**Request:** (To be implemented)
```json
{
  "code": "4/0AY0e-g7...",
  "state": "random_state_string"
}
```

**Response:** `200 OK` (To be implemented)
```json
{
  "status": "ok",
  "message": "YouTube account linked successfully"
}
```

---

### GET /api/v1/youtube/videos/{video_id}

Get YouTube video metadata.

**Authentication:** Required

**Response:** `200 OK` (To be implemented)
```json
{
  "id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "description": "Video description...",
  "is_live": true
}
```

---

## Sessions

**Note:** These endpoints are currently stubs. Expected schema based on `StreamingSession` model (`backend/app/db/models/streaming_session.py`).

### POST /api/v1/sessions

Create a new streaming session.

**Authentication:** Required

**Expected Request:**
```json
{
  "youtube_video_id": "dQw4w9WgXcQ",
  "title": "Live Q&A Session",
  "description": "Office hours for CS101"
}
```

**Expected Response:** `201 Created`
```json
{
  "id": "650e8400-e29b-41d4-a716-446655440001",
  "teacher_id": "550e8400-e29b-41d4-a716-446655440000",
  "youtube_video_id": "dQw4w9WgXcQ",
  "title": "Live Q&A Session",
  "description": "Office hours for CS101",
  "is_active": true,
  "started_at": "2025-12-31T10:00:00.000Z",
  "ended_at": null,
  "created_at": "2025-12-31T10:00:00.000Z",
  "updated_at": "2025-12-31T10:00:00.000Z"
}
```

---

### GET /api/v1/sessions

List streaming sessions for authenticated teacher.

**Authentication:** Required

**Query Parameters:**
- `is_active` (optional): Filter by active status (true/false)
- `limit` (optional): Maximum number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Expected Response:** `200 OK`
```json
{
  "sessions": [
    {
      "id": "650e8400-e29b-41d4-a716-446655440001",
      "youtube_video_id": "dQw4w9WgXcQ",
      "title": "Live Q&A Session",
      "is_active": true,
      "started_at": "2025-12-31T10:00:00.000Z",
      "ended_at": null
    }
  ],
  "total": 1
}
```

---

### GET /api/v1/sessions/{session_id}

Get details of a specific session.

**Authentication:** Required

**Expected Response:** `200 OK` (Full session object)

**Errors:**
- `404 Not Found`: Session doesn't exist or doesn't belong to teacher

---

### POST /api/v1/sessions/{session_id}/end

End an active streaming session.

**Authentication:** Required

**Expected Response:** `200 OK`
```json
{
  "id": "650e8400-e29b-41d4-a716-446655440001",
  "is_active": false,
  "ended_at": "2025-12-31T12:00:00.000Z"
}
```

---

## Comments

**Note:** Expected schemas based on `Comment` model (`backend/app/db/models/comment.py`).

### GET /api/v1/comments

Get comments for a session.

**Authentication:** Required

**Query Parameters:**
- `session_id` (required): UUID of the streaming session
- `is_question` (optional): Filter by question status (true/false)
- `is_answered` (optional): Filter by answered status (true/false)
- `limit` (optional): Maximum number of results (default: 100)
- `offset` (optional): Pagination offset (default: 0)

**Expected Response:** `200 OK`
```json
{
  "comments": [
    {
      "id": "750e8400-e29b-41d4-a716-446655440002",
      "session_id": "650e8400-e29b-41d4-a716-446655440001",
      "cluster_id": "850e8400-e29b-41d4-a716-446655440003",
      "youtube_comment_id": "UgxKREWPuILCdHgCoAEC",
      "author_name": "Student123",
      "author_channel_id": "UCxxxxx",
      "text": "What is the time complexity of quicksort?",
      "is_question": true,
      "is_answered": false,
      "confidence_score": 0.95,
      "published_at": "2025-12-31T10:15:00.000Z",
      "created_at": "2025-12-31T10:15:30.000Z"
    }
  ],
  "total": 1
}
```

---

## Clusters

**Note:** Expected schemas based on `Cluster` model (`backend/app/db/models/cluster.py`).

### GET /api/v1/clusters

Get question clusters for a session.

**Authentication:** Required

**Query Parameters:**
- `session_id` (required): UUID of the streaming session

**Expected Response:** `200 OK`
```json
{
  "clusters": [
    {
      "id": "850e8400-e29b-41d4-a716-446655440003",
      "session_id": "650e8400-e29b-41d4-a716-446655440001",
      "title": "Time Complexity Questions",
      "description": "Questions about algorithm time complexity",
      "similarity_threshold": 0.8,
      "comment_count": 5,
      "created_at": "2025-12-31T10:20:00.000Z",
      "updated_at": "2025-12-31T10:25:00.000Z"
    }
  ],
  "total": 1
}
```

---

## Answers

**Note:** Expected schemas based on `Answer` model (`backend/app/db/models/answer.py`).

### GET /api/v1/answers

Get AI-generated answers.

**Authentication:** Required

**Query Parameters:**
- `cluster_id` (optional): Filter by cluster
- `is_posted` (optional): Filter by posted status (true/false)

**Expected Response:** `200 OK`
```json
{
  "answers": [
    {
      "id": "950e8400-e29b-41d4-a716-446655440004",
      "cluster_id": "850e8400-e29b-41d4-a716-446655440003",
      "comment_id": null,
      "text": "The average time complexity of quicksort is O(n log n), while the worst case is O(n²)...",
      "youtube_comment_id": null,
      "is_posted": false,
      "posted_at": null,
      "created_at": "2025-12-31T10:30:00.000Z"
    }
  ],
  "total": 1
}
```

---

### POST /api/v1/answers/{answer_id}/post

Post an answer to YouTube as a comment.

**Authentication:** Required

**Expected Response:** `200 OK`
```json
{
  "id": "950e8400-e29b-41d4-a716-446655440004",
  "youtube_comment_id": "UgxNewCommentId",
  "is_posted": true,
  "posted_at": "2025-12-31T10:35:00.000Z"
}
```

---

## WebSocket

### WS /ws/{session_id}

Real-time bidirectional communication for live session updates.

**URL:** `ws://localhost:8000/ws/{session_id}?connection_id=optional`

**Authentication:** JWT token must be included as query parameter or in first message

**Connection Established Event:**

Server sends immediately upon successful connection:
```json
{
  "type": "connected",
  "timestamp": "2025-12-31T10:00:00.000Z",
  "data": {
    "connection_id": "conn_abc123",
    "session_id": "650e8400-e29b-41d4-a716-446655440001"
  },
  "message": "WebSocket connected successfully"
}
```

---

### Heartbeat (Ping/Pong)

Keep connection alive with periodic heartbeat.

**Client → Server (Ping):**
```json
{
  "type": "ping"
}
```

**Server → Client (Pong):**
```json
{
  "type": "pong",
  "timestamp": "2025-12-31T10:00:30.000Z",
  "data": {},
  "message": null
}
```

**Heartbeat Interval:** 30 seconds (configurable via `WEBSOCKET_HEARTBEAT_INTERVAL`)

---

### Event Types

Reference: `backend/app/services/websocket/events.py:8-31`

All events follow this base structure:
```json
{
  "type": "event_type",
  "timestamp": "2025-12-31T10:00:00.000Z",
  "data": { /* event-specific data */ },
  "message": "Human-readable message"
}
```

#### comment_created

New comment received from YouTube Live Chat.

```json
{
  "type": "comment_created",
  "timestamp": "2025-12-31T10:15:00.000Z",
  "data": {
    "id": "750e8400-e29b-41d4-a716-446655440002",
    "author_name": "Student123",
    "text": "What is the time complexity of quicksort?",
    "published_at": "2025-12-31T10:15:00.000Z"
  },
  "message": "New comment received"
}
```

#### comment_classified

Comment has been classified by AI as question/not-question.

```json
{
  "type": "comment_classified",
  "timestamp": "2025-12-31T10:15:05.000Z",
  "data": {
    "comment_id": "750e8400-e29b-41d4-a716-446655440002",
    "is_question": true,
    "confidence": 0.95
  },
  "message": "Comment classified as question"
}
```

#### cluster_created

New question cluster formed.

```json
{
  "type": "cluster_created",
  "timestamp": "2025-12-31T10:20:00.000Z",
  "data": {
    "id": "850e8400-e29b-41d4-a716-446655440003",
    "title": "Time Complexity Questions",
    "description": "Questions about algorithm time complexity",
    "comment_count": 1
  },
  "message": "New cluster created: Time Complexity Questions"
}
```

#### cluster_updated

Existing cluster updated with new comment.

```json
{
  "type": "cluster_updated",
  "timestamp": "2025-12-31T10:25:00.000Z",
  "data": {
    "id": "850e8400-e29b-41d4-a716-446655440003",
    "title": "Time Complexity Questions",
    "comment_count": 5
  },
  "message": "Cluster updated: Time Complexity Questions"
}
```

#### answer_ready

AI-generated answer is ready for teacher review.

```json
{
  "type": "answer_ready",
  "timestamp": "2025-12-31T10:30:00.000Z",
  "data": {
    "answer_id": "950e8400-e29b-41d4-a716-446655440004",
    "cluster_id": "850e8400-e29b-41d4-a716-446655440003",
    "text": "The average time complexity of quicksort is O(n log n)..."
  },
  "message": "Answer generated and ready for review"
}
```

#### answer_posted

Answer has been posted to YouTube comments.

```json
{
  "type": "answer_posted",
  "timestamp": "2025-12-31T10:35:00.000Z",
  "data": {
    "answer_id": "950e8400-e29b-41d4-a716-446655440004",
    "cluster_id": "850e8400-e29b-41d4-a716-446655440003"
  },
  "message": "Answer posted to YouTube"
}
```

#### quota_alert

Quota usage warning (sent at 80%, 90% thresholds).

```json
{
  "type": "quota_alert",
  "timestamp": "2025-12-31T10:40:00.000Z",
  "data": {
    "quota_type": "answer_generation",
    "used": 80,
    "limit": 100,
    "percentage": 80.0
  },
  "message": "Quota alert: answer_generation at 80.0%"
}
```

#### quota_exceeded

Quota limit has been reached.

```json
{
  "type": "quota_exceeded",
  "timestamp": "2025-12-31T11:00:00.000Z",
  "data": {
    "quota_type": "answer_generation",
    "used": 100,
    "limit": 100,
    "percentage": 100.0
  },
  "message": "Quota exceeded: answer_generation at 100.0%"
}
```

#### session_started / session_ended

Session lifecycle events.

```json
{
  "type": "session_started",
  "timestamp": "2025-12-31T10:00:00.000Z",
  "data": {
    "session_id": "650e8400-e29b-41d4-a716-446655440001"
  },
  "message": "Session started"
}
```

#### error

Error occurred during processing.

```json
{
  "type": "error",
  "timestamp": "2025-12-31T10:45:00.000Z",
  "data": {
    "error_code": "EMBEDDING_FAILED"
  },
  "message": "Failed to generate embedding for comment"
}
```

---

## Health & Monitoring

### GET /

Root endpoint returning application metadata.

**Response:** `200 OK`
```json
{
  "app_name": "AI Live Doubt Manager",
  "version": "1.0.0",
  "environment": "development",
  "status": "ok"
}
```

---

### GET /health

Health check endpoint for monitoring.

**Response:** `200 OK`
```json
{
  "status": "ok",
  "health": "healthy"
}
```

**Response:** `503 Service Unavailable` (if database or Redis unavailable)
```json
{
  "status": "error",
  "health": "unhealthy",
  "details": {
    "database": "disconnected",
    "redis": "connected"
  }
}
```

---

### GET /metrics

Prometheus metrics endpoint in text format.

**Response:** `200 OK` (text/plain)
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/sessions",status="200"} 42

# HELP websocket_connections_active Active WebSocket connections
# TYPE websocket_connections_active gauge
websocket_connections_active 5

# HELP queue_size_total Queue size
# TYPE queue_size_total gauge
queue_size_total{queue="classification"} 12
queue_size_total{queue="embedding"} 8

# HELP quota_usage Quota usage
# TYPE quota_usage gauge
quota_usage{teacher_id="550e...",quota_type="answer_generation"} 45
```

---

## Error Response Format

All API errors follow a consistent format:

**4xx/5xx Response:**
```json
{
  "detail": "Error message explaining what went wrong",
  "error_code": "OPTIONAL_ERROR_CODE"
}
```

**Common HTTP Status Codes:**
- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource doesn't exist
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

---

## Rate Limiting

All API endpoints are subject to rate limiting:

- **Default:** 60 requests per minute per IP/user
- **Burst:** 10 additional requests allowed

Rate limit headers included in responses:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704120000
```

**429 Response when exceeded:**
```json
{
  "detail": "Rate limit exceeded. Please retry after 30 seconds."
}
```

---

## References

- Auth schemas: `backend/app/schemas/auth.py`
- API routers: `backend/app/api/v1/`
- Database models: `backend/app/db/models/`
- WebSocket events: `backend/app/services/websocket/events.py`
- Configuration: `backend/app/core/config.py`
