# Architecture Overview

This document describes the system architecture of the AI Live Doubt Manager, a production-grade platform for managing live Q&A sessions during YouTube live streams using AI-powered question clustering and answer generation.

## System Overview

The AI Live Doubt Manager automatically collects questions from YouTube live chat, classifies them, groups similar questions into clusters, and generates AI-powered answers for educators to review and post back to the audience.

**Tech Stack:**
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL with pgvector, Redis
- **Workers:** Python async with Redis queues
- **Extension:** React, TypeScript, Chrome Manifest V3
- **Infrastructure:** Docker, Prometheus, Grafana
- **AI/ML:** OpenAI embeddings (1536-dim), cosine similarity clustering, RAG-based answer generation

---

## Core Components

### 1. Backend API (FastAPI)

**Location:** `backend/app/`

The Backend API is a FastAPI application providing RESTful endpoints and WebSocket connections for real-time communication.

#### Database Layer

**8 Core Models** (`backend/app/db/models/`):

1. **Teacher** - User accounts
   - Fields: id, email, name, hashed_password, is_active, is_verified
   - Password: bcrypt hashing with 12 rounds (configurable)
   - Relationships: 1:N with StreamingSession, YouTubeToken, Quota

2. **StreamingSession** - Live streaming sessions
   - Fields: id, teacher_id, youtube_video_id, title, description, is_active, started_at, ended_at
   - Relationships: N:1 with Teacher, 1:N with Comment and Cluster
   - Cascade: Deleting session deletes all comments and clusters

3. **Comment** - YouTube comments/questions
   - Fields: id, session_id, cluster_id, youtube_comment_id (unique), author_name, author_channel_id, text, is_question, is_answered, confidence_score, **embedding (Vector(1536))**, published_at
   - pgvector: Stores 1536-dimensional embeddings for semantic search
   - Relationships: N:1 with StreamingSession and Cluster, 1:N with Answer
   - Indexes: `idx_comment_session_question`, `idx_comment_session_answered`, `idx_comment_cluster`

4. **Cluster** - Groups of similar questions
   - Fields: id, session_id, title, description, similarity_threshold (default 0.8), **centroid_embedding (Vector(1536))**, comment_count
   - pgvector: Stores cluster centroid for similarity comparison
   - Relationships: N:1 with StreamingSession, 1:N with Comment and Answer
   - Cascade: Deleting cluster sets comment.cluster_id to NULL, deletes answers

5. **Answer** - AI-generated answers
   - Fields: id, cluster_id, comment_id, text, youtube_comment_id, is_posted, posted_at
   - Relationships: N:1 with Cluster and Comment
   - Index: `idx_answer_cluster_posted` for efficient queries

6. **Quota** - Usage quotas and rate limiting
   - Fields: id, teacher_id, quota_type, used, limit, period, reset_at
   - Unique constraint: (teacher_id, quota_type, period)
   - Index: `idx_quota_teacher_type`

7. **YouTubeToken** - OAuth tokens for YouTube API
   - Fields: id, teacher_id, access_token, refresh_token, expires_at
   - Encrypted storage for tokens (to be implemented)

8. **RAGDocument** - Knowledge base documents for RAG
   - Fields: id, content, metadata, embedding
   - Used for retrieval-augmented answer generation

**Key Database Features:**
- UUID primary keys for all tables
- Timezone-aware timestamps (UTC)
- pgvector extension for 1536-dim vector embeddings
- Strategic indexes for query performance
- CASCADE and SET NULL delete policies

#### Authentication & Security

**Implementation:** `backend/app/core/security.py`, `backend/app/api/v1/auth.py`

- **JWT Tokens:** Access token (30 min) + Refresh token (7 days)
- **Password Hashing:** bcrypt with configurable rounds (default 12)
- **Token Algorithm:** HS256 with SECRET_KEY
- **Protected Routes:** Require `Authorization: Bearer <token>` header
- **User Context:** Current user injected via dependency injection

#### API Routers

**Location:** `backend/app/api/v1/`

- `/auth` - Authentication (register, login, refresh, logout, me)
- `/youtube` - YouTube OAuth integration (stubs)
- `/sessions` - Session management (stubs)
- `/comments` - Comment management (stubs)
- `/clusters` - Cluster management (stubs)
- `/answers` - Answer management (stubs)
- `/ws/{session_id}` - WebSocket real-time communication (implemented)
- `/` - Root and health check
- `/health` - Health status
- `/metrics` - Prometheus metrics

#### WebSocket System

**Implementation:** `backend/app/services/websocket/`, `backend/app/api/v1/websocket.py`

**Features:**
- **Connection Manager:** Tracks active connections per session
- **Heartbeat:** Ping/pong every 30 seconds (configurable)
- **Event System:** 13 typed event types (see Event Types below)
- **Broadcasting:** Send to specific users or entire sessions
- **Connection Lifecycle:** connected, ping/pong, disconnected events

**Event Types** (`backend/app/services/websocket/events.py`):
- `comment_created` - New comment received
- `comment_classified` - Comment classified as question/not
- `cluster_created` - New cluster formed
- `cluster_updated` - Cluster updated with new comment
- `answer_ready` - AI answer ready for review
- `answer_posted` - Answer posted to YouTube
- `quota_alert` - Quota usage warning (80%, 90%)
- `quota_exceeded` - Quota limit reached
- `session_started` / `session_ended` - Session lifecycle
- `error` - Error occurred
- `ping` / `pong` - Heartbeat
- `connected` / `disconnected` - Connection lifecycle

**Event Format:**
```json
{
  "type": "event_type",
  "timestamp": "2025-12-31T10:00:00.000Z",
  "data": { /* event-specific data */ },
  "message": "Human-readable message"
}
```

#### Observability

**Prometheus Metrics** (`backend/app/core/metrics.py`):
- `http_requests_total` - HTTP request count by method/endpoint/status
- `http_request_duration_seconds` - Request latency histogram
- `websocket_connections_active` - Active WebSocket connections gauge
- `queue_size_total` - Queue backlog by queue name
- `worker_heartbeat` - Worker health check timestamp
- `quota_usage` - Quota consumption by teacher/type

**Structured Logging** (`backend/app/core/logging.py`):
- Development: Human-readable format
- Production: JSON format (`LOG_JSON=true`)
- RequestContextMiddleware: Adds request_id to all logs
- Log levels: DEBUG, INFO, WARNING, ERROR

---

### 2. Workers (Background Processing)

**Location:** `workers/`

Five specialized workers process tasks asynchronously via Redis queues. **Currently stubs awaiting Phase 2 AI integration.**

#### Worker Types

1. **Classification Worker** (`workers/classification/worker.py`)
   - **Purpose:** Classify comments as questions vs. non-questions
   - **Input:** `ClassificationPayload` (comment_id, text, session_id)
   - **Processing:** AI model classifies text → updates `Comment.is_question`, `confidence_score`
   - **Output:** Publishes to `embedding` queue if is_question=true
   - **Status:** Stub - awaiting AI model integration

2. **Embeddings Worker** (`workers/embeddings/worker.py`)
   - **Purpose:** Generate semantic embeddings for questions
   - **Input:** `EmbeddingPayload` (comment_id, text)
   - **Processing:** OpenAI API generates 1536-dim vector → stores in `Comment.embedding`
   - **Output:** Publishes to `clustering` queue
   - **Status:** Stub - awaiting OpenAI API integration

3. **Clustering Worker** (`workers/clustering/worker.py`)
   - **Purpose:** Group similar questions into clusters
   - **Input:** `ClusteringPayload` (session_id, comment_ids, trigger_type)
   - **Processing:**
     - Load question embeddings from database
     - Compute cosine similarity between questions
     - Group similar questions (threshold: 0.8)
     - Create/update `Cluster` with centroid_embedding
     - Assign `Comment.cluster_id`
   - **Output:** Publishes to `answer_generation` queue
   - **Status:** Stub - awaiting clustering algorithm implementation

4. **Answer Generation Worker** (`workers/answer_generation/worker.py`)
   - **Purpose:** Generate AI-powered answers using RAG
   - **Input:** `AnswerGenerationPayload` (cluster_id, session_id, question_texts)
   - **Processing:**
     - Retrieve relevant documents from `RAGDocument` using vector similarity
     - Generate answer using LLM with retrieved context
     - Create `Answer` record
     - Send `answer_ready` WebSocket event
   - **Output:** Answer ready for teacher review
   - **Status:** Stub - awaiting LLM integration

5. **Trigger Monitor Worker** (`workers/trigger_monitor/worker.py`)
   - **Purpose:** Monitor session metrics and trigger clustering
   - **Processing:**
     - Monitor comment count, time intervals
     - Trigger clustering when thresholds met (e.g., every 10 comments, every 5 minutes)
     - Publish to `clustering` queue
   - **Status:** Stub - awaiting implementation

#### Queue Infrastructure

**Queue Manager** (`workers/common/queue.py`):
- **Implementation:** Redis sorted sets with priority scoring
- **Priority:** Lower number = higher priority
- **Retry Logic:** Exponential backoff (1s, 2s, 4s), max 3 retries
- **Dead Letter Queue (DLQ):** Failed tasks after max retries
- **Operations:** enqueue, dequeue, peek, size, retry, move_to_dlq, clear

**Queue Names:**
- `comment_ingest` - New comments from YouTube
- `classification` - Comments to classify
- `embedding` - Questions to embed
- `clustering` - Clustering triggers
- `answer_generation` - Clusters needing answers
- `<queue>_dlq` - Dead letter queues

**Payload Schemas** (`workers/common/schemas.py`):
All payloads include: task_id, created_at, retry_count, max_retries

---

### 3. Chrome Extension (React/TypeScript)

**Location:** `chrome-extension/`

Browser extension providing teacher interface for managing live doubt sessions. **Currently stub awaiting Phase 4 implementation.**

#### Architecture

**Background Service Worker** (`src/background/`):
- `index.ts` - Initializes all background services
- `auth.ts` - OAuth authentication with backend
- `youtubePoller.ts` - Polls YouTube Live Chat API for new comments (stub)
- `websocket.ts` - WebSocket connection to backend for real-time updates (stub)
- `quota.ts` - Local quota tracking and alerts (stub)

**Content Script** (`src/content/`):
- `inject.ts` - Injects dashboard UI into YouTube pages

**Dashboard UI** (`src/dashboard/`):
- React components for teacher interface
- View live comments, question clusters, AI answers
- Session controls (start/stop)
- Quota monitoring

**API Client** (`src/api/`):
- `backend.ts` - HTTP client for backend API calls

#### Planned Workflow

1. Teacher navigates to YouTube Live video
2. Extension detects live video, creates session
3. Background worker polls Live Chat API every 5s
4. Fetches new comments → POSTs to backend `/api/v1/comments`
5. Backend stores comment → publishes to classification queue
6. Extension receives WebSocket events (`comment_created`, `cluster_created`, `answer_ready`)
7. Dashboard updates in real-time
8. Teacher reviews AI-generated answers → clicks "Post"
9. Extension POSTs answer to YouTube via API

#### Permissions & Manifest

- **Host Permissions:** `youtube.com`, `www.youtube.com`
- **APIs:** storage, tabs, scripting, identity
- **Manifest:** V3 (service worker architecture)

---

### 4. Shared Resources

**Location:** `shared/`

Cross-platform type definitions and constants ensuring consistency between backend and extension.

#### JSON Schemas (`shared/contracts/v1/`)

- `comment.json` - Comment data structure
- `cluster.json` - Cluster structure
- `answer.json` - Answer structure
- `websocket_event.json` - WebSocket event format

#### TypeScript Constants (`shared/constants/`)

- `rate_limits.ts` - API rate limiting thresholds (60/min, burst 10)
- `quota.ts` - Quota types and limits (poll, post, embedding, answer_generation)
- `thresholds.ts` - Processing thresholds (clustering triggers)

---

## Data Flow Architecture

### End-to-End Processing Pipeline

```
┌─────────────────┐
│ Teacher starts  │
│ YouTube Live    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Chrome Extension polls YouTube Live Chat API (every 5s)  │
│    - Fetches new comments                                   │
│    - Sends to Backend: POST /api/v1/comments               │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Backend API receives comment                             │
│    - Stores Comment in PostgreSQL                           │
│    - Publishes CommentIngestPayload to Redis classification │
│    - Sends comment_created WebSocket event                  │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Classification Worker                                     │
│    - Dequeues ClassificationPayload from classification     │
│    - AI model classifies: is_question (true/false)          │
│    - Updates Comment.is_question, confidence_score          │
│    - If is_question=true: publishes EmbeddingPayload        │
│    - Sends comment_classified WebSocket event               │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Embeddings Worker                                         │
│    - Dequeues EmbeddingPayload from embedding queue         │
│    - OpenAI API generates 1536-dim embedding vector         │
│    - Updates Comment.embedding (pgvector)                   │
│    - Publishes trigger to clustering queue                  │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Trigger Monitor Worker                                   │
│    - Monitors: comment count (e.g., every 10 questions)     │
│    - Monitors: time interval (e.g., every 5 minutes)        │
│    - When threshold met: publishes ClusteringPayload        │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Clustering Worker                                         │
│    - Loads question embeddings from Comment table           │
│    - Computes pairwise cosine similarity                    │
│    - Groups similar questions (threshold > 0.8)             │
│    - Creates/updates Cluster with centroid_embedding        │
│    - Assigns Comment.cluster_id                             │
│    - Publishes AnswerGenerationPayload                      │
│    - Sends cluster_created/cluster_updated WebSocket events │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Answer Generation Worker                                 │
│    - Retrieves relevant RAGDocuments using vector search    │
│    - Generates answer using LLM + retrieved context         │
│    - Creates Answer record (is_posted=false)                │
│    - Sends answer_ready WebSocket event                     │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Backend broadcasts via WebSocket                         │
│    - Extension receives answer_ready event                  │
│    - Dashboard shows new answer for review                  │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. Teacher Reviews & Posts                                  │
│    - Teacher reviews answer in dashboard                    │
│    - Clicks "Post to YouTube"                               │
│    - Extension: POST /api/v1/answers/{id}/post             │
│    - Backend: Posts to YouTube via API                      │
│    - Updates Answer.is_posted=true, youtube_comment_id      │
│    - Sends answer_posted WebSocket event                    │
└─────────────────────────────────────────────────────────────┘
```

### Database Relationships

```
Teacher
  ├── 1:N StreamingSession
  │     ├── 1:N Comment
  │     │     ├── N:1 Cluster (optional)
  │     │     └── 1:N Answer
  │     └── 1:N Cluster
  │           └── 1:N Answer (CASCADE delete)
  ├── 1:N YouTubeToken
  └── 1:N Quota

RAGDocument (independent, used for retrieval)
```

**Key Constraints:**
- Comment.youtube_comment_id: UNIQUE (prevents duplicates)
- Quota: UNIQUE (teacher_id, quota_type, period)
- StreamingSession DELETE → CASCADE to Comments and Clusters
- Cluster DELETE → SET NULL Comment.cluster_id, CASCADE to Answers

---

## Infrastructure

### Docker Compose Setup

**Services** (`docker-compose.yml`):

1. **postgres** - PostgreSQL 15 with pgvector
   - Port: 5432
   - Volume: postgres_data
   - Extension: CREATE EXTENSION vector

2. **redis** - Redis 7 Alpine
   - Port: 6379
   - Volume: redis_data
   - Config: `infra/docker/redis.conf`

3. **api** - FastAPI backend
   - Port: 8000
   - Build: `infra/docker/api.Dockerfile`
   - Depends: postgres, redis
   - Mounts: `./backend:/app/backend`

4. **workers** - Background workers
   - Build: `infra/docker/worker.Dockerfile`
   - Depends: postgres, redis
   - Mounts: `./workers`, `./backend`, `./shared`

**Networking:**
- All services on default bridge network
- Service discovery via service names (postgres, redis)

### Observability Stack

**Prometheus** (`infra/prometheus/`):
- Metrics collection from `/metrics` endpoint
- Scrape interval: 15s (configurable)
- Storage: Time-series database

**Grafana** (`infra/grafana/`):
- Visualization dashboards
- Data source: Prometheus
- Dashboards: API performance, worker health, quota usage, session metrics

**Grafana Dashboards:**
- **API Performance:** Request rates, latencies (p50, p95, p99), error rates by endpoint
- **Worker Health:** Queue sizes, processing rates, worker heartbeats, retry counts
- **Quota Usage:** Per-teacher consumption over time, quota exhaustion alerts
- **Session Metrics:** Active sessions, comment volumes, cluster counts, answer generation rates

### Terraform Infrastructure

**Location:** `infra/terraform/`

Infrastructure as code for cloud deployment (AWS/GCP/Azure):
- VPC and networking
- RDS PostgreSQL with pgvector
- ElastiCache Redis
- ECS/EKS for containers
- Load balancers
- CloudWatch/Stackdriver monitoring
- Secrets management

*Note: Terraform modules are defined but deployment configuration is environment-specific.*

---

## Configuration Management

**Implementation:** `backend/app/core/config.py`

Pydantic-based settings with environment variable loading:

**Key Configurations:**
- `ENVIRONMENT` - development/staging/production
- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_POOL_SIZE` - Connection pool size (default: 5)
- `DATABASE_POOL_PRE_PING` - Health check before using connection (true)
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret (MUST change in production)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - JWT access token TTL (30)
- `REFRESH_TOKEN_EXPIRE_DAYS` - JWT refresh token TTL (7)
- `PASSWORD_BCRYPT_ROUNDS` - Password hashing rounds (12)
- `CORS_ORIGINS` - Allowed CORS origins (list)
- `YOUTUBE_CLIENT_ID/SECRET` - YouTube OAuth credentials
- `DEFAULT_DAILY_ANSWER_LIMIT` - Default quota (100)
- `DEFAULT_MONTHLY_SESSION_LIMIT` - Default quota (30)
- `QUEUE_*` - Queue names (classification, embedding, clustering, etc.)
- `LOG_LEVEL` - Logging verbosity (INFO)
- `LOG_JSON` - JSON structured logging (false in dev, true in prod)
- `WEBSOCKET_HEARTBEAT_INTERVAL` - Ping interval in seconds (30)

**Environment Files:**
- `.env.development` - Development settings
- `.env.staging` - Staging settings
- `.env.production` - Production settings
- Loaded based on `ENVIRONMENT` variable

---

## Security Considerations

1. **Authentication:** JWT with secure secret key, token expiration
2. **Password Storage:** bcrypt with 12 rounds (configurable higher for production)
3. **API Keys:** YouTube credentials stored in environment, not in code
4. **CORS:** Strict origin whitelist
5. **Input Validation:** Pydantic schemas validate all inputs
6. **SQL Injection:** SQLAlchemy ORM prevents raw SQL vulnerabilities
7. **Rate Limiting:** 60 requests/min per user with burst allowance
8. **Quota Enforcement:** Prevents abuse of AI/YouTube APIs

---

## Scalability Considerations

**Horizontal Scaling:**
- **API:** Stateless, can scale to N instances behind load balancer
- **Workers:** Each worker type can scale independently based on queue size
- **WebSocket:** Requires sticky sessions or Redis pub/sub for multi-instance

**Database:**
- **Connection Pooling:** Prevents connection exhaustion
- **Indexes:** Optimized for common query patterns
- **pgvector:** Efficient vector similarity search at scale

**Queue Management:**
- **Priority Queues:** Critical tasks processed first
- **Backlog Monitoring:** Alert when queue_size > threshold
- **Auto-scaling:** Scale workers based on queue depth

**Caching (Future):**
- Redis cache for frequently accessed data
- Cluster centroids cached for fast similarity comparison

---

## Future Enhancements

**Phase 2: AI Integration (In Progress)**
- Complete classification worker with AI model
- Integrate OpenAI API for embeddings
- Implement clustering algorithm
- Build RAG-based answer generation

**Phase 3: YouTube Integration**
- Complete OAuth flow
- Implement live chat polling
- Add answer posting functionality
- YouTube quota management

**Phase 4: Chrome Extension**
- Build React dashboard UI
- Implement WebSocket real-time updates
- Add session controls
- Quota monitoring and alerts

**Phase 5: Advanced Features**
- Multi-language support
- Custom AI model fine-tuning
- Analytics and insights
- Admin dashboard

---

## References

- **Database Models:** `backend/app/db/models/` (8 models)
- **API Routers:** `backend/app/api/v1/` (auth, sessions, comments, etc.)
- **WebSocket Events:** `backend/app/services/websocket/events.py`
- **Worker Schemas:** `workers/common/schemas.py` (5 payload types)
- **Queue Management:** `workers/common/queue.py`
- **Configuration:** `backend/app/core/config.py`
- **Docker:** `docker-compose.yml`, `infra/docker/`
- **Monitoring:** `backend/app/core/metrics.py`
