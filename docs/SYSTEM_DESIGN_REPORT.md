# System Design Specification Report: AI Live Doubt Manager

> **Prepared for**: Senior Consultant Deep-Dive Audit
> **Date**: 2026-03-13
> **Stack**: FastAPI 0.115 / React 19 / PostgreSQL 15 (pgvector) / Redis 7 / Google Gemini AI
> **Scope**: Full-stack architecture — backend, worker pipeline, frontend, infrastructure

---

## 1. High-Level Architecture

### 1.1 Core Pattern: Event-Driven Pipeline with Real-Time Relay

The system follows a **producer-consumer pipeline architecture** with three distinct runtime tiers:

| Tier | Technology | Role |
|------|-----------|------|
| **API Tier** | FastAPI, uvicorn (2 workers) | HTTP/WS ingress, auth, CRUD, real-time relay |
| **Worker Tier** | 6 independent Python processes | Asynchronous AI processing pipeline |
| **Data Tier** | PostgreSQL 15 + Redis 7 | Persistence, coordination, pub/sub |

**Why this pattern**: Live YouTube sessions generate bursty comment traffic. Synchronous AI processing (classification → embedding → clustering → answer generation) would block API responses and create unacceptable latency. The pipeline decouples ingress from processing, allowing each stage to scale independently and fail independently without losing data — Redis queues persist tasks until consumed.

### 1.2 System Topology

```
YouTube Live Chat API
       │
  [Polling Worker] ──enqueue──▶ [Classification] ──▶ [Embedding] ──▶ [Clustering] ──▶ [Answer Gen] ──▶ [YT Posting]
       │                              │                   │               │                │                │
       ▼                              ▼                   ▼               ▼                ▼                ▼
   PostgreSQL ◀──────────── all workers write directly ──────────▶  Redis pub/sub ──▶ WS Manager ──▶ Browser
       ▲                                                                                    ▲
       │                                                                                    │
  [FastAPI API] ◀─── HTTP/WS ─── [React 19 SPA]                                            │
       │                              │                                                     │
       └─── Redis (queues, pub/sub, rate limits, quota, token blacklist, caching) ──────────┘
```

**Why direct DB writes from workers (not routing through the API)**: Workers need transactional guarantees — e.g., the clustering worker must atomically update the centroid vector and assign the comment in one transaction. Routing writes through the API would add latency, create a single point of failure, and complicate error handling. Each worker manages its own DB connection pool (`pool_size=2, max_overflow=3`) to keep total connections manageable.

### 1.3 Communication Patterns

| Pattern | Where Used | Why This Pattern |
|---------|-----------|-----------------|
| **Request-Response (HTTP)** | All API endpoints | Standard CRUD, synchronous auth flows |
| **Priority Queue (Redis ZSET)** | Worker pipeline (6 queues) | Ordered processing, priority support, atomic dequeue via `ZPOPMIN`. ZSET over LIST because it enables delayed retry (future timestamps as scores) |
| **Pub/Sub (Redis)** | WebSocket relay (`ws:{session_id}`) | Workers publish events; API subscriber delivers to browsers. Decouples worker processes from WebSocket connection state |
| **Polling (HTTP)** | YouTube Live Chat ingestion | YouTube API offers no webhooks for live chat; polling at 5s intervals is the only option. Capped at 10 concurrent threads via `ThreadPoolExecutor` |

---

## 2. Data Modeling & Persistence

### 2.1 PostgreSQL Schema (pgvector-enabled)

**Entity-Relationship Overview**:

```
Teachers (1) ──▶ (M) StreamingSessions (1) ──▶ (M) Comments
                                           (1) ──▶ (M) Clusters (1) ──▶ (M) Answers
Teachers (1) ──▶ (1) YouTubeTokens
Teachers (1) ──▶ (M) Quotas
Teachers (1) ──▶ (M) RAGDocuments
Comments (M) ──▶ (1) Clusters  [SET NULL on cluster delete]
```

**Vector-enabled tables**:

| Model | Column | Dimensions | Index | Purpose |
|-------|--------|-----------|-------|---------|
| `comments` | `embedding` | Vector(768) | HNSW (cosine_ops, m=16, ef=64) | Semantic similarity for clustering |
| `clusters` | `centroid_embedding` | Vector(768) | HNSW (cosine_ops, m=16, ef=64) | Running centroid for nearest-centroid matching |
| `rag_documents` | `embedding` | Vector(768) | HNSW (cosine_ops, m=16, ef=64) | Cosine distance retrieval for answer grounding |

**Why 768 dimensions (not Gemini's native 3072)**: 768 is the balance point — reduces storage and index cost by ~75% while retaining sufficient semantic fidelity for question clustering (not fine-grained retrieval). The code explicitly normalizes embeddings post-generation because Google requires normalization for non-3072 dimensions.

**Why pgvector over a dedicated vector DB (Qdrant, Pinecone, etc.)**: The system already requires PostgreSQL for relational data. pgvector eliminates an infrastructure dependency. At the expected scale (hundreds to low thousands of comments per session), sequential scan is fast enough. The tradeoff: pgvector cannot handle billion-scale ANN, but this system doesn't need it.

### 2.2 Key Schema Design Decisions

| Decision | Implementation | Why |
|----------|---------------|-----|
| `youtube_comment_id` NOT NULL + UNIQUE | Manual comments use `f"manual:{uuid4()}"` prefix | Enables idempotent ingestion — polling worker checks for existing ID before insert, preventing duplicates across polling cycles |
| `Cluster.comment_count` denormalized | Updated atomically in clustering worker | Centroid update formula `(old * n + new) / (n + 1)` needs `n` in the same transaction. `COUNT(*)` would be slower and subject to phantom reads |
| Answers persisted before posting | `is_posted` boolean + async YouTube posting | Separates "answer generated" (always succeeds) from "answer posted" (may fail due to quota/auth). Dashboard shows pending answers immediately |
| CASCADE on `session_id` | Deleting session removes all child data | Session deletion is a "nuke everything" operation |
| SET NULL on `cluster_id` | Cluster deletion preserves comments | Comments may be re-clustered; destroying them would lose data |
| Fernet encryption on YouTube tokens | `encrypt_data`/`decrypt_data` via `backend/app/core/encryption.py` | A DB breach without the encryption key cannot expose YouTube OAuth tokens |

### 2.3 Composite Indexes

```
idx_session_teacher_active     (teacher_id, is_active)     — session list queries
idx_comment_session_question   (session_id, is_question)   — clustering worker queries
idx_comment_session_answered   (session_id, is_answered)    — dashboard stats
idx_comment_cluster            (cluster_id)                 — cluster detail views
idx_answer_cluster_posted      (cluster_id, is_posted)      — pending answers filter
idx_quota_teacher_type         (teacher_id, quota_type)     — quota lookups
```

### 2.4 Redis Usage Map (6 Distinct Roles)

| Role | Key Pattern | Data Structure | TTL | Why Redis |
|------|------------|---------------|-----|-----------|
| Task queues | `classification`, `embedding`, etc. | Sorted Set (ZSET) | None | Priority ordering via `score = priority * 1M + timestamp` |
| Dead letter queues | `{queue}_dlq` | ZSET | None | Failed task inspection after 3 retries |
| Rate limiting | `ratelimit:{ip}` | String (INCR) | 60s | Sliding window counter, per-IP |
| YouTube quota | `yt_quota:{teacher_id}:{date}` | String (INCRBY) | TTL to midnight | Per-teacher daily quota (10,000 units) |
| Token blacklist | `blacklist:token:{hash}` | String | Token's remaining TTL | JWT logout revocation (Redis GET per request) |
| YouTube cache | `youtube:poll:{session_id}:*` | String | 3600s | Caches `live_chat_id` to avoid repeated API calls (1 unit each) |
| WebSocket relay | `ws:{session_id}` | Pub/Sub channel | N/A | Cross-process event delivery to browsers |
| CSRF state | `yt_state:{state}` | String | 600s | OAuth flow protection (10 min window) |

**Why `volatile-lru` eviction policy**: Queue entries have no TTL and are protected from eviction. TTL-bearing keys (rate limits, cached chat IDs) are evictable under memory pressure — acceptable because they are regenerable.

---

## 3. Component Interactions

### 3.1 API Layer — Middleware Stack

Execution order (outermost → innermost):

1. **RateLimitMiddleware** (`backend/app/core/rate_limit_middleware.py`) — Redis-backed IP throttling (60 req/min). Skips `/health`, `/metrics`, `/docs`. **Why outermost**: Reject abusive traffic before auth or DB work.
2. **RequestContextMiddleware** (`backend/app/core/middleware.py`) — Injects `X-Request-ID` and tracks execution time via `contextvars`. **Why**: Distributed tracing without a full APM solution.
3. **CORSMiddleware** — Configured origins from env (`:5173` for Vite dev, `:8000`, `:8080`).

### 3.2 Auth Flow

```
Client ──Bearer token──▶ HTTPBearer ──▶ verify_token() ──▶ Redis blacklist check ──▶ DB Teacher lookup ──▶ is_active check
```

**Why Redis blacklist**: JWTs are stateless; without a blacklist, a logged-out token remains valid until expiry. Cost: one Redis GET per authenticated request.

**Multi-tenancy enforcement**: Every data-access endpoint JOINs to `StreamingSession` to verify `teacher_id == current_user.id`. This is the authorization boundary — there are no role-based permissions beyond ownership.

### 3.3 Worker Pipeline Detail

```
[1. Classification]  Gemini 2.5-flash: "Is this a question?" → {is_question, confidence}
        │             GATE: Only enqueues if is_question=True (filters ~60-70% of comments)
        ▼
[2. Embedding]       Gemini embedding-001: text → 768-dim normalized vector
        │             IDEMPOTENT: Skips if comment.embedding already exists
        ▼
[3. Clustering]      pgvector cosine distance against session's cluster centroids
        │             Threshold ≥ 0.65 → join cluster; < 0.65 → create new
        │             Centroid update: new = normalize((old * n + vec) / (n + 1))
        │             Triggers answer gen on: new cluster OR milestones {3, 10, 25}
        ▼
[4. Answer Gen]      RAG: top-5 nearest documents by centroid embedding
        │             Two-prompt: with-context vs. without-context (prevents hallucination)
        │             Semaphore: max 5 concurrent Gemini calls
        │             Auto-enqueues to YT posting if teacher has YouTube connected
        ▼
[5. YT Posting]      Posts to YouTube Live Chat (200 char limit)
        │             Publishes WebSocket event on success
        ▼
      Done

[6. YT Polling]      Independent 5s cycle, ThreadPoolExecutor (max 10 threads)
                      Deduplicates via youtube_comment_id UNIQUE constraint
                      Token auto-refresh on HTTP 401
```

**Why milestones {3, 10, 25}**: At 3, the cluster has enough signal for a meaningful title (also generated here). At 10 and 25, accumulated question variants provide richer context for a more comprehensive answer. This avoids regenerating on every question (Gemini quota) while updating answers as understanding deepens.

**Why semaphore(5)**: Rate-limits Gemini API calls across all threads sharing a `GeminiClient` instance. Uses `threading.Semaphore` (not asyncio) because workers are synchronous Python processes.

### 3.4 WebSocket Relay Architecture

```
Worker process ──publish──▶ Redis channel "ws:{session_id}" ──subscribe──▶ API process ──broadcast──▶ Browser WS clients
```

**Why not direct worker-to-browser**: Workers are separate OS processes (potentially separate containers). They have no access to the API's in-memory WebSocket registry. Redis pub/sub provides the cross-process bridge. Multiple API instances each subscribe independently and deliver to their own local connections — natural load distribution.

**WebSocket auth**: Client sends `{"type": "auth", "token": "<jwt>"}` as first message. **Why first-message auth over query param**: Query params appear in server logs and browser history.

### 3.5 YouTube OAuth Flow

```
Frontend ──GET /youtube/auth/url──▶ Backend generates OAuth URL + CSRF state (Redis, 10min TTL)
     │
     ▼  (popup window)
Google OAuth consent ──redirect──▶ Backend callback validates state, exchanges code
     │                              Encrypts tokens (Fernet), stores in DB
     ▼                              Returns HTML that postMessages to opener
Frontend receives message, closes popup, updates connection status
```

---

## 4. State Management & AI/ML Memory

### 4.1 Online Learning — No Model Persistence

The system uses **online nearest-centroid clustering**, not batch KMeans. State is the centroid vectors stored in the `clusters` table:

```python
# Centroid update formula (workers/clustering/worker.py)
new_centroid = (old_centroid * comment_count + new_embedding) / (comment_count + 1)
normalized_centroid = new_centroid / ||new_centroid||
```

**Why online over batch KMeans**: Live sessions require immediate clustering of each incoming question. Batch KMeans would require periodic re-processing of all comments. The tradeoff: online nearest-centroid is order-dependent (different insertion orders produce different clusters), but for grouping similar student questions in real-time, this is acceptable.

### 4.2 RAG Architecture

```
Teacher uploads document ──▶ Chunked + embedded (768-dim) ──▶ Stored in rag_documents table
                                                                       │
Answer Generation Worker ──pgvector cosine distance──▶ Top 5 nearest docs by cluster centroid
                                                                       │
                                              ┌─────────────────────────┘
                                              ▼
                              Two-prompt system:
                              ├─ WITH context: "Answer using only the provided context"
                              └─ WITHOUT context: "No context available, use general knowledge"
```

**Why centroid as query vector (not individual question text)**: The centroid represents the semantic center of all questions in the cluster. This retrieves documents relevant to the cluster's *theme*, not just one question's phrasing.

**Why two separate prompts**: A single prompt with optional context leads to inconsistent behavior — the model may hallucinate when no context is provided, or ignore context when it exists. Explicit prompts produce predictable outputs.

### 4.3 Gemini Model Usage

| Operation | Model | Where | Concurrency |
|-----------|-------|-------|-------------|
| Classification | `gemini-2.5-flash` | Classification worker | Sequential (1 at a time) |
| Embeddings | `gemini-embedding-001` | Embedding worker | Sequential |
| Cluster summarization | `gemini-2.0-flash` | Clustering worker (at count=3) | Sequential |
| Answer generation | `gemini-2.5-flash` | Answer generation worker | Semaphore(5) |

All operations use `tenacity` retry: 3 attempts, exponential backoff 1s → 10s.

### 4.4 Frontend State Architecture

| Scope | Mechanism | What Lives Here |
|-------|-----------|----------------|
| **Global** | `AuthContext` | JWT token, user email/name, login/logout/register |
| **Global** | `ThemeContext` | dark/light mode (localStorage, cross-tab sync) |
| **Session-scoped** | `DashboardPage` state | activeSession, sessionEvents (cap 200), quotaAlert |
| **Component-local** | `useState` hooks | Fetch states, forms, UI toggles, caches |
| **Real-time** | `useWebSocket` hook | WS messages (cap 100), connected/reconnecting status |

**Why refetch-on-WS-event (not pure WS-driven state)**: WS events are notifications ("something changed"), not complete state snapshots. Debounced refetching (500-2000ms) ensures the dashboard always shows authoritative server state, preventing drift from missed or out-of-order messages.

**Why localStorage for JWT (not httpOnly cookie)**: The WebSocket auth flow requires JavaScript access to the token (sent as first WS message). httpOnly cookies cannot be read by JavaScript.

---

## 5. Infrastructure & DevOps

### 5.1 Docker Compose Services

| Service | Image | Port | Key Config |
|---------|-------|------|-----------|
| `postgres` | `pgvector/pgvector:pg15` | 127.0.0.1:5432 | `max_connections=100`, volume: `postgres_data` |
| `redis` | `redis:7-alpine` | 127.0.0.1:6379 | `maxmemory 256mb`, `volatile-lru`, RDB snapshots |
| `api` | Custom (Python 3.13-slim) | 8000 | `uvicorn --workers 2` |
| `workers` | Custom (Python 3.13-slim) | None | `python -m workers.runner` (all 6 workers in one container) |

**Why `max_connections=100`**: Connection budget is 15 (API) + 30 (workers) = 45 active. 100 provides ~2x headroom for admin connections, migrations, and monitoring.

**Why single workers container**: Development simplicity. Production should separate workers into individual containers for independent scaling and failure isolation.

**Why `volatile-lru`**: Queue entries (no TTL) are protected from eviction. TTL-bearing keys (rate limits, caches) are evictable under memory pressure — they are regenerable.

### 5.2 CI/CD Pipeline (GitHub Actions)

```
[Lint Job]                              [Test Job]
  Python 3.13                             Python 3.13
  black + isort + ruff                    Services: pgvector:pg15 + redis:7
  Checks: backend/, workers/              pytest backend/tests workers -v
  Line length: 119 chars                  Dummy GEMINI_API_KEY
```

**Lint → Test** dependency chain. Both jobs run on push.

### 5.3 Configuration Management

`backend/app/core/config.py` — Pydantic `BaseSettings` with `@lru_cache` singleton.

Key configuration groups:
- **Database**: pool_size=5, max_overflow=10, pool_recycle=3600s, pool_pre_ping=True
- **Redis**: max_connections=10, decode_responses=True
- **Security**: HS256, access_token=30min, refresh_token=7d, bcrypt_rounds=12
- **Gemini**: api_key, model names, clustering_threshold
- **YouTube**: client_id, client_secret, redirect_uri
- **WebSocket**: heartbeat_interval=30s, timeout=300s
- **Rate limiting**: requests_per_minute, enabled flag
- **Encryption**: encryption_key (≥32 chars, validated at startup)

Environment loading: `.env.{environment}` files with fallback.

---

## 6. Critical Paths

### 6.1 Path 1: Comment → Posted Answer (Highest Complexity)

**Stages**: YouTube comment → Polling worker → DB insert → Classification → Embedding → Clustering → Answer generation → YouTube posting → WebSocket notification

**Latency budget**: ~10-30 seconds total. Gemini API calls dominate: classification (~500ms), embedding (~300ms), answer generation (~2-5s). Each inter-stage hop adds ~1s (poll interval).

**Failure recovery**: Tasks remain in Redis queues on worker crash (ZPOPMIN is atomic). `tenacity` retries transient Gemini failures. Queue-level retry (3 attempts, 60s delay) catches persistent failures. DLQ captures exhausted retries for manual inspection.

### 6.2 Path 2: WebSocket Real-Time Delivery

**Risk**: Redis pub/sub is fire-and-forget. If the API subscriber task crashes or disconnects, events are lost during reconnection (exponential backoff, max 30s). Frontend's debounced refetch partially mitigates stale data.

### 6.3 Path 3: YouTube OAuth Token Lifecycle

**Risk**: If the encryption key (`settings.encryption_key[:32]`) is lost or changed, all stored YouTube tokens become undecryptable, severing all YouTube connections system-wide. The key must be treated as infrastructure state, not a rotatable secret.

---

## 7. Potential Bottlenecks & Availability Risks

### 7.1 Single-Threaded Worker Bottleneck — **SEVERITY: HIGH**

Each pipeline worker is a single-threaded Python process. During traffic spikes (popular live session, hundreds of comments/minute), the classification worker becomes the bottleneck — ~2 comments/second throughput (Gemini-bound). A spike of 10 comments/second creates a growing backlog.

**Mitigation**: Horizontal scaling — run multiple instances per worker. `ZPOPMIN`-based dequeue is safe for concurrent consumers. No code changes needed.

### 7.2 Redis Pub/Sub Message Loss — **SEVERITY: MEDIUM**

Pub/sub delivers only to currently connected subscribers. API restart = lost events during reconnection window. Dashboard may show stale data.

**Mitigation**: Replace pub/sub with Redis Streams (`XADD`/`XREAD` with consumer groups). Streams persist messages and support "read from last acknowledged" semantics.

### 7.3 pgvector HNSW Index Tuning — **SEVERITY: LOW (resolved)**

HNSW indexes have been added to all three vector columns (`comments.embedding`, `clusters.centroid_embedding`, `rag_documents.embedding`) using `vector_cosine_ops` with tuning parameters `m=16, ef_construction=64`. This resolves the original sequential scan concern.

**Remaining risk**: At very high scale (O(100K+) vectors per table), HNSW `ef_search` may need tuning for query latency. Monitor clustering worker query times.

### 7.4 YouTube Quota Exhaustion — **SEVERITY: MEDIUM**

Daily quota: 10,000 units/teacher. Poll cost: 5 units. At 5-second intervals: `5 × (86400/5) = 86,400 units/day` — **far exceeding the limit**. Polling effectively stops after ~2000 polls (~2.8 hours).

**Mitigation**: Use YouTube API's `pollingIntervalMillis` response field for adaptive polling. Implement exponential backoff when no new messages arrive.

### 7.5 Gemini API as Single Point of Failure — **SEVERITY: HIGH**

All AI operations depend on one Gemini API key. Key revocation, rate limiting, or Gemini outage stalls the entire pipeline. `tenacity` handles transient failures but not sustained outages.

**Mitigation**: Circuit breaker pattern with degraded-mode fallbacks (e.g., regex-based classification). Multiple API keys with rotation.

### 7.6 Connection Pool Exhaustion Under Scale — **SEVERITY: LOW-MEDIUM**

Current budget: 45/100 connections. Each horizontally-scaled worker instance adds 5 connections. 11+ additional instances exhaust the pool.

**Mitigation**: Deploy PgBouncer for connection multiplexing between workers and PostgreSQL.

### 7.7 JWT in localStorage — **SEVERITY: LOW (security note)**

localStorage is vulnerable to XSS. A single XSS vulnerability exposes the JWT. However, this is a deliberate tradeoff — WebSocket auth requires JavaScript access to the token, and httpOnly cookies cannot be read by JS.

**Mitigation**: Strict CSP headers, input sanitization, and regular XSS audits. Consider a dual-auth scheme (cookie for HTTP, short-lived token for WS).

---

## Appendix: Key File Paths

| Component | Path |
|-----------|------|
| API entry point | `backend/app/main.py` |
| Configuration | `backend/app/core/config.py` |
| Auth & security | `backend/app/core/security.py`, `encryption.py` |
| Database models | `backend/app/db/models/*.py` |
| API routes | `backend/app/api/v1/*.py` |
| WebSocket manager | `backend/app/services/websocket/manager.py` |
| Gemini AI client | `backend/app/services/gemini/client.py` |
| YouTube services | `backend/app/services/youtube/client.py`, `oauth.py`, `quota.py` |
| Queue infrastructure | `workers/common/queue.py` |
| Worker payloads | `workers/common/schemas.py` |
| Classification worker | `workers/classification/worker.py` |
| Embedding worker | `workers/embeddings/worker.py` |
| Clustering worker | `workers/clustering/worker.py` |
| Answer generation worker | `workers/answer_generation/worker.py` |
| YouTube polling worker | `workers/youtube_polling/worker.py` |
| YouTube posting worker | `workers/youtube_posting/worker.py` |
| Frontend entry | `frontend/src/main.jsx` → `App.jsx` |
| API service layer | `frontend/src/services/api.js` |
| WebSocket hook | `frontend/src/hooks/useWebSocket.js` |
| Dashboard page | `frontend/src/pages/DashboardPage.jsx` |
| Docker Compose | `docker-compose.yml` |
| CI/CD | `.github/workflows/ci.yml` |

---

## 8. Scaling Roadmap

### 8.1 Current Capacity Baseline

| Resource | Current Limit | Utilization | Headroom |
|----------|--------------|-------------|----------|
| Gemini API concurrency | 5 (semaphore) | Burst-dependent | Low under load |
| YouTube quota | 10,000 units/teacher/day | 5 units/poll × 12 polls/min = 3,600/hr | Exhausts in ~2.8 hrs |
| DB connections (API) | 5 + 10 overflow = 15 | Request-dependent | 55 of 100 unused |
| DB connections (Workers) | 6 × (2 + 3) = 30 | Steady | See above |
| Redis memory | 256 MB | ~70-200 KB for queues | Ample |
| API rate limit | 60 req/min/IP | Per-IP | No per-user limiting |
| Worker throughput | 1 process per stage | ~2 comments/sec (Gemini-bound) | Backlog at >2/sec |

### 8.2 Phase 1: Quick Wins (Week 1-2)

| Change | Current | Target | Effort | Impact |
|--------|---------|--------|--------|--------|
| Gemini semaphore | 5 | 15-20 | 1 line (`client.py:30`) | 3-4x answer gen throughput |
| YouTube poll interval | 5s fixed | Adaptive (use API's `pollingIntervalMillis`) | Medium | 50-70% quota savings |
| Redis memory | 256 MB | 512 MB | Config change | 2x headroom |
| Worker pool size | 2+3 | 5+5 per worker | Config change (`common/db.py`) | Handle connection bursts |
| PostgreSQL max_connections | 100 | 200 | Docker config | Support horizontal workers |

### 8.3 Phase 2: Horizontal Scaling (Month 1-2)

**Worker horizontal scaling** — The ZPOPMIN-based queue dequeue is inherently safe for concurrent consumers. No code changes needed to run N instances of any worker:

```
# Scale classification to 3 instances
docker-compose up --scale classification-worker=3
```

**Requires**: Split `workers` Docker service into per-worker services. Current single-container design bundles all 6 workers.

**PgBouncer for connection multiplexing** — Each new worker instance adds 5 DB connections. At 20+ worker instances, PostgreSQL's 100-connection limit is reached. PgBouncer in transaction mode multiplexes many worker connections over fewer PostgreSQL connections.

```
Workers (100 connections) → PgBouncer (20 connections) → PostgreSQL
```

**Redis Sentinel for HA** — Single Redis instance is a SPOF for all queues, pub/sub, rate limits, and quota tracking. Redis Sentinel provides automatic failover with minimal configuration.

### 8.4 Phase 3: High Volume (Month 3-6, 1000+ concurrent users)

| Component | Strategy | Trigger |
|-----------|----------|---------|
| Comments table | Partition by `session_id` (range) | >10M rows |
| Embeddings | Local model fallback (e.g., `all-MiniLM-L6-v2`) | Gemini cost > $100/day |
| YouTube quota | Quota tiering (premium teachers get 50K/day) | Teachers hitting limits daily |
| Worker autoscaling | Scale on queue depth (>100 tasks → spawn pod) | Sustained backlog |
| pgvector | Tune HNSW `ef_search` parameter | >100K vectors per table |
| Redis | Redis Cluster (sharding) | >1GB memory or >50K ops/sec |
| API | Multiple uvicorn instances behind load balancer | >500 concurrent WebSocket connections |

### 8.5 Phase 4: Multi-Region (Month 6-12)

- **Database**: Read replicas for dashboard queries, write primary for ingestion
- **Workers**: Deploy regionally, share Redis Cluster
- **CDN**: Frontend static assets via CloudFront/Cloudflare
- **Gemini API**: Multi-key rotation across regions for quota distribution

---

## 9. Cost Modeling

### 9.1 Gemini API Costs

**Per-comment pipeline cost** (assuming ~60% of comments are questions):

| Operation | Model | Input Tokens (est.) | Output Tokens (est.) | Cost/Call |
|-----------|-------|-------------------|---------------------|-----------|
| Classification | gemini-2.5-flash | ~100 | ~30 | ~$0.000015 |
| Embedding | gemini-embedding-001 | ~100 | N/A | ~$0.000010 |
| Cluster summary | gemini-2.0-flash | ~200 | ~20 | ~$0.000005 |
| Answer generation | gemini-2.5-flash | ~500 (with RAG context) | ~200 | ~$0.000060 |

**Per-session cost estimate** (1-hour session, 500 comments):

| Stage | Calls | Cost |
|-------|-------|------|
| Classification | 500 | $0.0075 |
| Embedding | 300 (60% questions) | $0.003 |
| Cluster summaries | ~30 clusters | $0.00015 |
| Answer generation | ~60 (30 clusters × 1-2 milestones) | $0.0036 |
| **Total per session** | **~890 calls** | **~$0.014** |

**Monthly projection** (10 teachers, 5 sessions/week each):

```
10 teachers × 5 sessions/week × 4 weeks × $0.014 = $2.80/month (Gemini only)
```

At scale (100 teachers, 10 sessions/week): **~$56/month** in Gemini costs.

### 9.2 YouTube Quota Cost Analysis

**Per-session quota burn** (1 hour, 5-second polling):

| Operation | Calls | Units | Total |
|-----------|-------|-------|-------|
| Polling | 720 (3600s ÷ 5s) | 5 | 3,600 |
| Get chat ID | 1 (cached after first) | 1 | 1 |
| Post answers | ~30 (1 per cluster) | 50 | 1,500 |
| **Total** | | | **5,101 units** |

**Daily capacity**: 10,000 units → ~1.96 sessions/day at current polling rate.

**With adaptive polling** (10s average): ~3.5 sessions/day.

**With YouTube-recommended interval** (~15-30s): ~5-8 sessions/day.

### 9.3 Infrastructure Costs (Docker/Cloud)

| Component | Minimum Spec | Est. Monthly Cost (AWS) |
|-----------|-------------|------------------------|
| PostgreSQL (pgvector) | db.t3.medium (2 vCPU, 4GB) | ~$50 |
| Redis | cache.t3.micro (0.5GB) | ~$15 |
| API (ECS/EC2) | t3.small (2 vCPU, 2GB) | ~$20 |
| Workers (ECS/EC2) | t3.medium (2 vCPU, 4GB) | ~$35 |
| Frontend (S3 + CloudFront) | Static hosting | ~$5 |
| **Total** | | **~$125/month** |

### 9.4 Cost Optimization Opportunities

| Optimization | Savings | Effort |
|-------------|---------|--------|
| Embedding cache by text hash (avoid re-embedding identical questions) | 10-30% Gemini cost | Low |
| Local embedding model fallback (sentence-transformers) | 90% embedding cost | Medium |
| Adaptive YouTube polling (back off when idle) | 50-70% quota savings | Low |
| Batch classification (group 5-10 comments per Gemini call) | 60-80% classification cost | Medium |
| Gemini response caching (identical question patterns) | 20-40% answer gen cost | Medium |

---

## 10. Threat Model (STRIDE Analysis)

### 10.1 Threat Matrix

#### Spoofing

| Threat | Vector | Severity | Current Mitigation | Gap |
|--------|--------|----------|-------------------|-----|
| JWT token theft | XSS → localStorage access | **HIGH** | Token blacklist on logout | Token in localStorage is XSS-vulnerable |
| Teacher impersonation | Stolen refresh token (7-day lifetime) | **HIGH** | Refresh token rotation (not implemented) | No refresh token rotation on use |
| WebSocket hijacking | Intercepted auth message | **MEDIUM** | First-message JWT auth + ownership check | No message-level encryption (relies on WSS) |
| OAuth state forgery | Brute-force 128-bit state | **LOW** | 10-min TTL + single-use deletion | Secure by design |

#### Tampering

| Threat | Vector | Severity | Current Mitigation | Gap |
|--------|--------|----------|-------------------|-----|
| Answer text injection | Edit answer endpoint with malicious content | **MEDIUM** | Auth + ownership check | No content sanitization before YouTube posting |
| Comment text overflow | Unbounded text field in schema | **MEDIUM** | SQLAlchemy Text column (no DB limit) | No `max_length` on CommentCreate schema |
| Cluster centroid poisoning | Submit adversarial embeddings via manual questions | **LOW** | Online centroid averaging dilutes adversarial inputs | Requires many adversarial inputs to shift centroid significantly |
| Queue payload manipulation | Direct Redis access | **LOW** | Redis bound to 127.0.0.1 | No authentication on Redis (password not configured) |

#### Repudiation

| Threat | Vector | Severity | Current Mitigation | Gap |
|--------|--------|----------|-------------------|-----|
| Denied answer approval | Teacher claims they didn't approve a post | **MEDIUM** | `posted_at` timestamp on Answer model | No audit log of who approved what |
| Session data deletion | Teacher deletes session (CASCADE) | **LOW** | Intentional feature | No soft-delete or audit trail |

#### Information Disclosure

| Threat | Vector | Severity | Current Mitigation | Gap |
|--------|--------|----------|-------------------|-----|
| YouTube token exposure | Database breach | **HIGH** | Fernet encryption at rest | Encryption key in env var — single key for all tokens |
| Cross-tenant data leakage | Broken ownership check | **HIGH** | JOIN-based ownership verification on all endpoints | Relies on developer discipline (no automated test) |
| JWT secret exposure | Env var leak / config dump | **HIGH** | Single HS256 secret in settings | No key rotation mechanism |
| Error message leakage | Unhandled exceptions in API | **MEDIUM** | FastAPI default error handling | Debug mode configurable — ensure `debug=False` in production |

#### Denial of Service

| Threat | Vector | Severity | Current Mitigation | Gap |
|--------|--------|----------|-------------------|-----|
| API rate limit bypass | Distributed IPs | **HIGH** | Per-IP rate limiting (60/min) | No per-user or per-session rate limiting |
| WebSocket flood | Send thousands of messages per second | **HIGH** | None detected | No per-connection message rate limit |
| Queue flooding | Rapid manual question submission (10/request, no cooldown) | **MEDIUM** | Max 10 questions per request | No per-session cooldown or daily limit |
| YouTube quota exhaustion | Create many sessions with polling | **MEDIUM** | Quota check per poll | No limit on concurrent active sessions per teacher |
| Gemini API exhaustion | Trigger thousands of classifications | **MEDIUM** | Semaphore(5) limits concurrency | No per-teacher Gemini call budget |

#### Elevation of Privilege

| Threat | Vector | Severity | Current Mitigation | Gap |
|--------|--------|----------|-------------------|-----|
| Access other teacher's data | Modify session_id in API calls | **HIGH** | Ownership JOIN on every query | No RBAC — only owner/not-owner model |
| Admin escalation | No admin role exists | **N/A** | Single-role system (teacher only) | No admin panel or elevated access |
| Worker process compromise | Worker has direct DB write access | **MEDIUM** | Workers share DB credentials with API | No least-privilege DB users per component |

### 10.2 Top 5 Actionable Recommendations

| Priority | Recommendation | Addresses | Effort |
|----------|---------------|-----------|--------|
| **P0** | Add `max_length` validation on all text fields in Pydantic schemas | Tampering, DoS | Low |
| **P0** | Add per-connection WebSocket message rate limit (e.g., 10 msg/sec) | DoS | Low |
| **P1** | Migrate JWT from localStorage to SessionStorage; add CSP headers | Spoofing | Medium |
| **P1** | Add Redis AUTH password in production | Tampering | Low |
| **P2** | Implement audit log table for answer approvals and session deletions | Repudiation | Medium |

### 10.3 Security Configuration Checklist (Production Deployment)

```
[ ] Set debug=False in FastAPI
[ ] Set LOG_JSON=True for structured logging
[ ] Set CORS origins to production domain only
[ ] Configure Redis AUTH password
[ ] Ensure ENCRYPTION_KEY is unique per environment (≥32 chars)
[ ] Ensure SECRET_KEY is unique per environment
[ ] Set RATE_LIMIT_ENABLED=True
[ ] Verify PostgreSQL connections are SSL-encrypted
[ ] Disable /docs and /redoc endpoints in production
[ ] Add CSP, X-Frame-Options, X-Content-Type-Options headers
[ ] Configure HTTPS termination (TLS 1.2+)
[ ] Set up log aggregation for security event monitoring
```
