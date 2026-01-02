# Failure Modes and Recovery

This document describes potential failure scenarios, detection methods, recovery mechanisms, and monitoring strategies for the AI Live Doubt Manager system.

---

## Backend API Failures

### Database Connection Loss

**Symptom:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Detection:**
- SQLAlchemy connection pool errors
- Health check endpoint returns 503
- Database operation timeouts
- Prometheus metric: `database_connections_active` drops to 0

**Recovery Mechanism:**

Implementation: `backend/app/db/session.py`

- **pool_pre_ping=True**: Tests connection before using from pool (config: `DATABASE_POOL_PRE_PING`)
- **Automatic Reconnection**: Connection pool attempts reconnect automatically
- **Exponential Backoff**: Retry intervals: 5s, 10s, 20s, 40s (max)
- **Health Check**: `GET /health` returns 503 when DB unavailable

**Impact:**
- All database operations fail
- API returns `503 Service Unavailable`
- Workers cannot process tasks (require DB access)
- WebSocket connections remain active but cannot fetch data

**Fallback:**
- API continues running (doesn't crash)
- Health endpoint indicates unhealthy status
- Clients can retry requests automatically

**Configuration:**
```python
# backend/app/core/config.py:34
database_pool_pre_ping: bool = True  # Health check before using connection
database_pool_size: int = 5
database_max_overflow: int = 10
database_pool_recycle: int = 3600  # Recycle connections every hour
```

**Monitoring:**
```promql
# Alert when database connections drop
database_connections_active < 1

# Alert on connection errors
rate(database_errors_total[5m]) > 10
```

---

### Redis Unavailability

**Symptom:** `redis.exceptions.ConnectionError: Error connecting to Redis`

**Detection:**
- Redis connection errors
- Queue operations timeout
- Worker heartbeats stop
- Prometheus metric: `redis_connections_active == 0`

**Recovery Mechanism:**

Implementation: `workers/common/redis.py`

- **Retry Logic**: 3 attempts with exponential backoff (1s, 2s, 4s)
- **Connection Pool**: Reuses connections, attempts reconnect on failure
- **Graceful Degradation**: Workers log errors and wait for Redis to recover

**Impact:**
- Queue operations fail → workers stop processing
- Rate limiting may be disabled (if Redis-based)
- WebSocket pub/sub may degrade to in-memory only (if multi-instance)
- Quota tracking may be delayed

**Fallback:**
- API can switch to in-memory rate limiting (degraded)
- Workers log errors and retry periodically
- Critical operations can use database as fallback (slower)

**Configuration:**
```python
# backend/app/core/config.py:37-42
redis_url: str = "redis://localhost:6379/0"
redis_max_connections: int = 10
redis_decode_responses: bool = True
```

**Monitoring:**
```promql
# Alert when Redis unavailable
redis_connections_active == 0

# Alert on queue operation failures
rate(redis_errors_total[5m]) > 5
```

---

### JWT Token Issues

**Symptoms:**
- `401 Unauthorized: Invalid token`
- `401 Unauthorized: Token expired`
- `401 Unauthorized: Malformed token`

**Detection:**
- JWT verification failures in auth middleware
- Signature validation errors
- Token expiration checks fail

**Recovery Mechanism:**

Implementation: `backend/app/core/security.py`

**For Clients:**
1. **Access Token Expired** (after 30 min):
   - Client should use refresh token via `POST /api/v1/auth/refresh`
   - Receive new access token and continue

2. **Refresh Token Expired** (after 7 days):
   - Client must re-authenticate via `POST /api/v1/auth/login`
   - Prompt user for credentials

3. **Invalid Signature** (SECRET_KEY changed):
   - All tokens invalidated
   - All users must re-authenticate
   - **Prevention**: Never change SECRET_KEY in production without migration plan

**Impact:**
- Specific user affected (not system-wide unless SECRET_KEY changed)
- User sees "Session expired" message
- Chrome extension prompts re-login

**Error Messages:**
- `401: "Invalid token"` - Malformed or wrong signature
- `401: "Token expired"` - Access token past expiry
- `401: "Invalid refresh token"` - Refresh token expired or invalid

**Configuration:**
```python
# backend/app/core/config.py:45-51
secret_key: str = "change-me-in-production"  # MUST be strong random key
algorithm: str = "HS256"
access_token_expire_minutes: int = 30
refresh_token_expire_days: int = 7
```

---

## Worker Failures

### Worker Crash

**Symptom:** Worker process terminates unexpectedly

**Detection:**
- Process monitoring (Docker restart logs)
- Worker heartbeat metric stops updating
- Queue items not being processed
- Prometheus alert: `worker_heartbeat > 60s ago`

**Recovery Mechanism:**

Implementation: `docker-compose.yml`

- **Docker Restart Policy**: `restart: unless-stopped`
- **Automatic Restart**: Docker restarts crashed workers immediately
- **Supervisor (Alternative)**: Can use supervisord for more control
- **Health Checks**: Periodic heartbeat updates to Prometheus

**Impact:**
- Processing delays while worker restarts (typically <5 seconds)
- Queue backlog grows during downtime
- Tasks in progress may be lost (will retry from queue)

**Monitoring:**
```yaml
# docker-compose.yml
workers:
  restart: unless-stopped
```

```promql
# Alert when worker heartbeat missing
time() - worker_heartbeat > 60

# Alert when worker restarts frequently
rate(worker_restarts_total[5m]) > 3
```

**Prevention:**
- Proper exception handling in worker code
- Resource limits to prevent OOM kills
- Logging to identify crash causes

---

### Queue Overflow

**Symptom:** Queue size grows unbounded, processing lags behind ingestion

**Detection:**
- `queue_size` metric exceeds threshold (e.g., >10,000)
- Queue depth alert from Grafana
- Processing latency increases

**Recovery Mechanism:**

Implementation: Prometheus metrics + manual intervention

**Immediate Actions:**
1. **Scale Workers Horizontally**: Add more worker containers
   ```bash
   docker-compose up --scale workers=5
   ```

2. **Pause YouTube Polling**: Stop comment ingestion temporarily
   - Extension reduces polling frequency
   - Or disable polling until queue clears

3. **Increase Worker Resources**: Allocate more CPU/memory

**Long-term Solutions:**
- Auto-scaling based on queue depth
- Rate limit comment ingestion at source
- Optimize worker processing speed

**Impact:**
- Increasing latency between comment received and answer generated
- Users see delays in dashboard updates
- Quota may exhaust faster due to backlog processing

**Mitigation:**
```python
# workers/common/queue.py
# Monitoring queue size
queue_size = manager.size('classification')
if queue_size > 5000:
    alert_admins('Queue backlog detected')
```

**Monitoring:**
```promql
# Alert when queue > 10,000 items
queue_size_total{queue="classification"} > 10000

# Alert when queue growing rapidly
rate(queue_size_total[5m]) > 100
```

---

### Worker Processing Failure

**Symptom:** Task fails during processing (e.g., API error, validation error)

**Detection:**
- Exception in worker code
- Task retry_count increments
- After 3 failures, moved to dead letter queue (DLQ)

**Recovery Mechanism:**

Implementation: `workers/common/queue.py`

**Retry Logic:**
- **Max Retries**: 3 attempts (configurable via `max_retries` in payload)
- **Retry Delays**: Exponential backoff - 1s, 2s, 4s
- **Dead Letter Queue**: Tasks exceeding max retries moved to `<queue>_dlq`

**Workflow:**
1. Task fails during processing
2. Worker calls `queue.retry(queue_name, payload, delay=60)`
3. Payload `retry_count` incremented
4. If `retry_count < max_retries`: Re-enqueue with delay
5. If `retry_count >= max_retries`: Move to DLQ

**Impact:**
- Specific comment/question may not be classified/embedded/clustered
- Teacher may need to manually handle the question
- DLQ tasks require admin review

**Fallback:**
- Admin can view DLQ and manually retry or skip
- Failed embeddings can be regenerated later
- Failed answers can be manually written

**Configuration:**
```python
# workers/common/queue.py:22-23
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 60  # seconds
```

**Monitoring:**
```promql
# Alert on high retry rate
rate(queue_retries_total[5m]) > 10

# Alert when DLQ growing
queue_size_total{queue=~".*_dlq"} > 50
```

---

## Chrome Extension Failures

### WebSocket Disconnection

**Symptom:** Dashboard shows "Reconnecting..." or stale data

**Detection:**
- `connection.close` event fired
- Ping timeout (no pong received within 30s)
- Network error in browser console

**Recovery Mechanism:**

Implementation: `chrome-extension/src/background/websocket.ts` (stub)

**Reconnection Strategy:**
- **Exponential Backoff**: 1s, 2s, 4s, 8s, 16s, max 30s
- **Automatic Reconnection**: Attempts to reconnect indefinitely
- **Heartbeat**: Sends ping every 30s, expects pong within 5s

**Workflow:**
1. WebSocket connection lost
2. Extension detects disconnection
3. Wait initial delay (1s)
4. Attempt reconnection
5. If fails, double delay (2s, 4s, ...)
6. Max delay capped at 30s
7. UI shows "Reconnecting..." badge

**Impact:**
- No real-time updates (comment_created, cluster_created, answer_ready events)
- Dashboard shows stale data until reconnection
- User can still use extension but misses live updates

**Fallback:**
- Poll API endpoints as backup (less efficient)
- Show "offline mode" indicator
- Queue actions to send when reconnected

**Configuration:**
```python
# backend/app/core/config.py:90-91
websocket_heartbeat_interval: int = 30  # seconds
websocket_timeout: int = 300  # 5 minutes
```

**UI Indicators:**
- Green badge: "Connected"
- Orange badge: "Reconnecting..."
- Red badge: "Disconnected (offline mode)"

---

### YouTube API Quota Exceeded

**Symptom:** `403 Forbidden` with `quotaExceeded` error from YouTube API

**Detection:**
- HTTP 403 response from YouTube Live Chat API
- Error response contains `quotaExceeded` error code
- YouTube quota dashboard shows limit reached

**Recovery Mechanism:**

Implementation: `chrome-extension/src/background/youtubePoller.ts` (stub)

**Immediate Response:**
1. Stop polling YouTube API immediately
2. Display quota exceeded warning in dashboard
3. Show countdown to quota reset (midnight Pacific Time)

**Workflow:**
1. YouTube API returns 403 quotaExceeded
2. Extension detects error
3. Disable polling until reset_at timestamp
4. Log error with timestamp
5. Show user-friendly message in UI

**Impact:**
- No new comments fetched from YouTube
- Existing data and clusters still work
- AI processing continues for existing comments
- Teacher cannot get new questions until reset

**Fallback:**
- Manual comment entry (teacher pastes questions)
- Reduce polling frequency (e.g., every 30s instead of 5s)
- Request quota increase from Google

**Quotas (YouTube Data API v3):**
- **Default:** 10,000 units/day
- **Live Chat API cost:** 5 units per request
- **Max requests:** 2,000 polls/day at default quota

**Monitoring:**
- Extension logs quota usage locally
- Backend tracks POLL quota (system quota, separate from YouTube)
- Alert admins when quota exhaustion is frequent

**UI:**
```
⚠️ YouTube API Quota Exceeded
Daily limit reached. Polling paused until reset at 12:00 AM PT.
Consider reducing polling frequency or requesting quota increase.
```

---

### Background Service Worker Sleep

**Symptom:** Extension stops responding, polling pauses, WebSocket disconnects

**Detection:**
- Service worker becomes inactive (Chrome DevTools)
- Alarms stop firing
- WebSocket disconnection

**Recovery Mechanism:**

Implementation: Chrome Manifest V3 service worker limitations

**Chrome Limitation:**
- Service workers sleep after 5 minutes of inactivity
- Cannot maintain long-lived connections

**Workarounds:**
1. **Alarms API**: Schedule periodic wakeups
   ```javascript
   chrome.alarms.create('keepAlive', { periodInMinutes: 1 });
   chrome.alarms.onAlarm.addListener(() => { /* wake up */ });
   ```

2. **User Interaction**: Keep active during active sessions
3. **Message Passing**: Wake on messages from content script

**Impact:**
- Polling may pause during session
- WebSocket may disconnect and need reconnection
- Some real-time updates delayed

**Mitigation:**
```javascript
// chrome-extension/src/background/index.ts (stub)
chrome.alarms.create('heartbeat', { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'heartbeat') {
    // Keep service worker alive
    checkActiveSession();
  }
});
```

---

## Data Consistency Issues

### Duplicate Comments

**Symptom:** Same YouTube comment received multiple times

**Detection:**
- Database unique constraint violation on `Comment.youtube_comment_id`
- Insert fails with duplicate key error

**Recovery Mechanism:**

Implementation: `backend/app/db/models/comment.py:32`

- **Unique Constraint**: `youtube_comment_id` must be unique
- **Error Handling**: Catch duplicate key error, ignore insert
- **Idempotent Processing**: Safe to receive same comment multiple times

**Impact:**
- No impact - duplicate safely ignored
- Database maintains integrity
- No duplicate processing

**Logging:**
```python
try:
    db.add(comment)
    db.commit()
except IntegrityError:
    logger.info(f"Duplicate comment ignored: {youtube_comment_id}")
    db.rollback()
```

---

### Orphaned Clusters

**Symptom:** Cluster exists but has no comments (all deleted or moved)

**Detection:**
- Cluster.comment_count == 0
- Query finds clusters with zero related comments

**Recovery Mechanism:**

Implementation: Scheduled cleanup task (to be implemented)

**Cleanup Strategy:**
```python
# backend/app/tasks/cleanup.py (to be implemented)
# Delete clusters with no comments
clusters_to_delete = db.query(Cluster).filter(Cluster.comment_count == 0).all()
for cluster in clusters_to_delete:
    db.delete(cluster)  # Cascade deletes answers
```

**Impact:**
- Minimal - just database clutter
- Orphaned clusters don't affect functionality
- Cascade delete removes associated answers

**Prevention:**
- Update `comment_count` when comments added/removed
- Periodic cleanup job runs daily

---

### Embedding Generation Failure

**Symptom:** OpenAI API error, network timeout, rate limit

**Detection:**
- Exception during OpenAI API call
- HTTP 429 (rate limit) or 500 error
- Network timeout after 30s

**Recovery Mechanism:**

Implementation: `workers/embeddings/worker.py` (stub)

**Retry Strategy:**
1. Retry 3 times with exponential backoff
2. After 3 failures, mark comment with `embedding_failed` flag (optional field)
3. Move to DLQ for manual review

**Impact:**
- Comment cannot be clustered (requires embedding)
- Question remains unclustered, shows individually in dashboard
- Teacher can still see and answer manually

**Fallback:**
- Allow manual re-triggering via API
- Admin can regenerate embeddings in batch
- Comments without embeddings still accessible

**Monitoring:**
```promql
# Alert on high embedding failure rate
rate(embedding_failures_total[5m]) > 10
```

---

## Monitoring & Alerting

### Prometheus Metrics to Monitor

Implementation: `backend/app/core/metrics.py`

| Metric | Threshold | Alert |
|--------|-----------|-------|
| `queue_size_total` | > 5,000 | Queue backlog building |
| `worker_heartbeat` | > 60s ago | Worker may be dead |
| `quota_usage/quota_limit` | > 0.9 | Quota nearly exceeded |
| `http_request_duration_seconds` | > 2s (p95) | API slow |
| `websocket_connections_active` | == 0 (session active) | No clients connected |
| `database_connections_active` | < 1 | Database unavailable |
| `redis_connections_active` | == 0 | Redis unavailable |
| `worker_restarts_total` | rate > 3/5m | Worker crashing frequently |

### Grafana Dashboards

**1. API Performance Dashboard:**
- Request rates (requests/sec by endpoint)
- Latencies (p50, p95, p99 by endpoint)
- Error rates (4xx, 5xx percentages)
- Active WebSocket connections

**2. Worker Health Dashboard:**
- Queue sizes (line chart over time)
- Processing rates (items/sec by queue)
- Worker heartbeats (last update time)
- Retry counts (failures by queue)
- DLQ sizes (items in dead letter queues)

**3. Quota Usage Dashboard:**
- Per-teacher quota consumption (line charts)
- Quota exhaustion events (table)
- Quota percentage used (gauges)
- Teachers approaching limits (> 80% list)

**4. Session Metrics Dashboard:**
- Active sessions count
- Comment volumes (comments/min)
- Cluster formation rate
- Answer generation rate
- Teacher activity heatmap

### Logging Strategy

Implementation: `backend/app/core/logging.py`

**Log Levels:**
- **DEBUG**: Detailed debugging (development only)
- **INFO**: Normal operations (user actions, task completions)
- **WARNING**: Unexpected but handled (retries, fallbacks)
- **ERROR**: Failures requiring attention (unhandled exceptions)

**Structured Logging (Production):**
```json
{
  "timestamp": "2025-12-31T10:15:30.000Z",
  "level": "ERROR",
  "message": "Database connection failed",
  "request_id": "req_abc123",
  "teacher_id": "550e8400...",
  "error": "OperationalError: connection refused",
  "stack_trace": "..."
}
```

**Request Context:**
- `RequestContextMiddleware` adds `request_id` to all logs during request
- Enables tracing single request through entire system

**Configuration:**
```python
# backend/app/core/config.py:82-83
log_level: str = "INFO"
log_json: bool = False  # True in production for structured logs
```

---

## Incident Response Checklist

When production incident occurs:

### 1. Detect & Alert
- [ ] Prometheus alert fired
- [ ] Check Grafana dashboards for anomalies
- [ ] Identify affected component (API, workers, database, Redis)

### 2. Assess Impact
- [ ] How many users affected?
- [ ] Which features unavailable?
- [ ] Data loss risk?

### 3. Immediate Response
- [ ] Check service health: `curl http://localhost:8000/health`
- [ ] Check Docker containers: `docker-compose ps`
- [ ] Check logs: `docker-compose logs --tail=100 api workers`
- [ ] Check queue sizes: `redis-cli LLEN classification`

### 4. Common Fixes
- [ ] Restart services: `docker-compose restart api workers`
- [ ] Clear stuck queues: `redis-cli DEL classification`
- [ ] Scale workers: `docker-compose up --scale workers=5`
- [ ] Check database: `psql -d ai_doubt_manager -c "SELECT 1"`

### 5. Post-Incident
- [ ] Document root cause
- [ ] Update runbooks
- [ ] Add monitoring/alerts to prevent recurrence
- [ ] Review logs for patterns

---

## References

- **Database Session:** `backend/app/db/session.py` (connection pool config)
- **Redis Client:** `workers/common/redis.py` (retry logic)
- **Queue Manager:** `workers/common/queue.py` (retry, DLQ)
- **WebSocket Events:** `backend/app/services/websocket/events.py`
- **Metrics:** `backend/app/core/metrics.py`
- **Logging:** `backend/app/core/logging.py`
- **Configuration:** `backend/app/core/config.py`
- **Docker:** `docker-compose.yml` (restart policies)
