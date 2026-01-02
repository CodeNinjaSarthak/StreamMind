# Quota Model

## Overview

The quota system manages usage limits for different operations to prevent abuse of AI APIs and YouTube APIs. Quotas are tracked per teacher account and reset automatically based on their period (hourly or daily).

**Purpose:**
- Prevent excessive API usage costs (OpenAI, YouTube)
- Ensure fair resource allocation across users
- Protect system from abuse
- Provide visibility into usage patterns

---

## Quota Types

Reference: `shared/constants/quota.ts`, `backend/app/core/config.py`

The system defines four quota types:

### 1. POLL

- **Operation:** YouTube Live Chat polling
- **Purpose:** Limit frequency of fetching comments from YouTube API
- **Period:** Hourly
- **Default Limit:** 1000 requests/hour
- **Cost per Operation:** 1 unit

### 2. POST

- **Operation:** Posting messages to YouTube comments
- **Purpose:** Limit answer posting to prevent spam
- **Period:** Hourly
- **Default Limit:** 100 posts/hour
- **Cost per Operation:** 10 units

### 3. EMBEDDING

- **Operation:** Text embedding generation via OpenAI
- **Purpose:** Control OpenAI API costs
- **Period:** Daily
- **Default Limit:** 10,000 embeddings/day
- **Cost per Operation:** 1 unit

### 4. ANSWER_GENERATION

- **Operation:** AI answer generation via LLM
- **Purpose:** Control LLM API costs and quality
- **Period:** Daily
- **Default Limit:** 500 answers/day (configurable)
- **Cost per Operation:** 5 units

---

## Database Model

Reference: `backend/app/db/models/quota.py`

Quotas are stored in the `quotas` table with the following schema:

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `teacher_id` | UUID | Foreign key to teachers table |
| `quota_type` | String(50) | Type: poll, post, embedding, answer_generation |
| `used` | Integer | Current usage count (incremented on each operation) |
| `limit` | Integer | Maximum allowed usage for the period |
| `period` | String(20) | Reset period: hourly, daily, monthly |
| `reset_at` | DateTime(TZ) | Timestamp when quota resets |
| `created_at` | DateTime(TZ) | Record creation timestamp |
| `updated_at` | DateTime(TZ) | Last update timestamp |

### Constraints

- **Unique Constraint:** `(teacher_id, quota_type, period)` - Ensures one quota per type per period per teacher
- **Index:** `idx_quota_teacher_type` on `(teacher_id, quota_type)` for fast lookups

### Relationships

- **N:1 with Teacher:** Each quota belongs to one teacher
- **Cascade Delete:** When teacher deleted, all quotas are deleted

### Example Records

```sql
-- Teacher has hourly POLL quota
id: 550e8400-e29b-41d4-a716-446655440000
teacher_id: 123e4567-e89b-12d3-a456-426614174000
quota_type: 'poll'
used: 245
limit: 1000
period: 'hourly'
reset_at: '2025-12-31T11:00:00Z'

-- Teacher has daily ANSWER_GENERATION quota
id: 650e8400-e29b-41d4-a716-446655440001
teacher_id: 123e4567-e89b-12d3-a456-426614174000
quota_type: 'answer_generation'
used: 87
limit: 100
period: 'daily'
reset_at: '2026-01-01T00:00:00Z'
```

---

## Limits and Costs

### Default Limits

Reference: `backend/app/core/config.py:71-72`

**System Defaults (applied to new teacher accounts):**
- `DEFAULT_DAILY_ANSWER_LIMIT`: 100 answers/day
- `DEFAULT_MONTHLY_SESSION_LIMIT`: 30 sessions/month

**Operational Limits:**
- POLL_PER_HOUR: 1,000 requests
- POST_PER_HOUR: 100 requests
- EMBEDDING_PER_DAY: 10,000 requests
- ANSWER_GENERATION_PER_DAY: 500 requests (or custom default)

### Operation Costs

Each operation consumes quota units:

| Operation | Quota Type | Cost (units) |
|-----------|-----------|--------------|
| Fetch comments from YouTube | POLL | 1 |
| Post answer to YouTube | POST | 10 |
| Generate text embedding | EMBEDDING | 1 |
| Generate AI answer | ANSWER_GENERATION | 5 |

**Example:** If a teacher generates 20 answers in a day, they consume `20 × 5 = 100 units` of their ANSWER_GENERATION quota.

---

## Reset Schedule

Quotas automatically reset based on their period type:

### Hourly Quotas (POLL, POST)

- **Reset Frequency:** Every hour at the top of the hour
- **Example:** Quota used at 10:45 AM resets at 11:00 AM
- **Reset Logic:**
  - `used` field set to 0
  - `reset_at` updated to next hour (current_hour + 1)

### Daily Quotas (EMBEDDING, ANSWER_GENERATION)

- **Reset Frequency:** Every day at midnight UTC
- **Example:** Quota used on Dec 31 resets on Jan 1 at 00:00:00 UTC
- **Reset Logic:**
  - `used` field set to 0
  - `reset_at` updated to next day at midnight UTC

### Reset Implementation

**Scheduled Task** (To be implemented in `backend/app/tasks/quota_reset.py`):
- Runs as periodic background task (cron-like)
- Queries quotas where `reset_at <= current_time`
- Resets `used = 0` for expired quotas
- Updates `reset_at` to next reset time
- Logs reset events for audit trail

**Alternative:** Database triggers or application-level checks before quota enforcement.

---

## Enforcement

### How Quotas are Checked

**Before Operation:**
```python
# Pseudocode
quota = get_quota(teacher_id, quota_type)
if quota.used >= quota.limit:
    raise QuotaExceededError
```

**After Operation:**
```python
# Pseudocode
quota.used += operation_cost
save(quota)

# Send WebSocket alert if approaching limit
if quota.used / quota.limit >= 0.8:
    send_quota_alert(quota_type, quota.used, quota.limit)
```

### Enforcement Flow

1. **Request Received:** Teacher attempts operation (e.g., generate answer)
2. **Check Quota:** Query `quotas` table for `(teacher_id, quota_type)`
3. **Validate:** If `used < limit`, allow operation; else reject with 429 error
4. **Execute Operation:** Perform the requested operation
5. **Increment Usage:** `used += operation_cost`
6. **Update Database:** Save updated quota record
7. **Send Alerts:** If usage crosses threshold (80%, 90%, 100%), send WebSocket event

### Error Responses

**429 Too Many Requests** (Quota exceeded):
```json
{
  "detail": "Quota exceeded for answer_generation. Limit: 100, Used: 100. Resets at 2026-01-01T00:00:00Z",
  "error_code": "QUOTA_EXCEEDED",
  "quota_type": "answer_generation",
  "used": 100,
  "limit": 100,
  "reset_at": "2026-01-01T00:00:00Z"
}
```

### WebSocket Integration

Reference: `backend/app/services/websocket/events.py:172-193`

The system sends real-time quota alerts via WebSocket:

#### quota_alert Event

Sent when usage reaches 80% or 90% of limit:

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

#### quota_exceeded Event

Sent when limit is reached:

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

**Client Handling:**
- Chrome extension receives quota events via WebSocket
- Dashboard displays warning badges (orange at 80%, red at 90%)
- Shows countdown to quota reset
- Disables "Post Answer" button when quota exceeded

---

## Monitoring

### Prometheus Metrics

Reference: `backend/app/core/metrics.py`

**Metric:** `quota_usage`
- **Type:** Gauge
- **Labels:** `teacher_id`, `quota_type`
- **Description:** Current quota usage count

**Example Queries:**
```promql
# Current usage for teacher
quota_usage{teacher_id="123...", quota_type="answer_generation"}

# Percentage used
(quota_usage / quota_limit) * 100

# Alert when > 90%
quota_usage / quota_limit > 0.9
```

### Logging

**Quota Events Logged:**
- Quota checked: `{"event": "quota_check", "teacher_id": "...", "quota_type": "poll", "used": 45, "limit": 1000}`
- Quota incremented: `{"event": "quota_increment", "quota_type": "answer_generation", "cost": 5, "new_used": 55}`
- Quota exceeded: `{"event": "quota_exceeded", "quota_type": "post", "used": 100, "limit": 100}`
- Quota reset: `{"event": "quota_reset", "quota_type": "embedding", "previous_used": 8543, "reset_at": "..."}`

### Grafana Dashboard

**Quota Usage Dashboard:**
- Line chart: Usage over time by quota type
- Gauge: Current usage percentage
- Table: All teachers approaching quota limits (> 80%)
- Alerts: Notify admins when multiple teachers hit limits (system capacity issue)

---

## Admin Operations

### Manually Adjust Quota

Admins can modify quotas for specific teachers:

```sql
-- Increase answer generation limit for premium teacher
UPDATE quotas
SET limit = 500
WHERE teacher_id = '123e4567-e89b-12d3-a456-426614174000'
  AND quota_type = 'answer_generation';

-- Reset quota early (e.g., after user reports issue)
UPDATE quotas
SET used = 0, reset_at = NOW() + INTERVAL '1 day'
WHERE teacher_id = '123e4567-e89b-12d3-a456-426614174000'
  AND quota_type = 'embedding';
```

### View Quota Status

```sql
-- Check quota status for a teacher
SELECT quota_type, used, limit,
       ROUND((used::float / limit) * 100, 2) as percentage_used,
       reset_at
FROM quotas
WHERE teacher_id = '123e4567-e89b-12d3-a456-426614174000'
ORDER BY percentage_used DESC;
```

### Quota Exhaustion Analysis

```sql
-- Find teachers frequently hitting limits
SELECT teacher_id, quota_type, COUNT(*) as exceeded_count
FROM quota_logs
WHERE event = 'quota_exceeded'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY teacher_id, quota_type
HAVING COUNT(*) > 10
ORDER BY exceeded_count DESC;
```

---

## Future Enhancements

1. **Tiered Quotas:** Different limits for free/premium/enterprise users
2. **Burst Allowance:** Temporary quota increases for short periods
3. **Quota Purchases:** Allow users to buy additional quota
4. **Smart Throttling:** Gradually slow down operations as limit approaches instead of hard cutoff
5. **Quota Sharing:** Allow quota pooling across team members
6. **Historical Analytics:** Track quota usage trends over weeks/months

---

## References

- **Database Model:** `backend/app/db/models/quota.py`
- **Configuration:** `backend/app/core/config.py:71-72` (default limits)
- **Constants:** `shared/constants/quota.ts` (quota types)
- **WebSocket Events:** `backend/app/services/websocket/events.py:172-193`
- **Metrics:** `backend/app/core/metrics.py` (`quota_usage` gauge)
