# AI Live Doubt Manager — Documentation

> Master navigation index. Find the right file by asking "what question am I answering?"

---

## Quick Navigation

| Question | File |
|----------|------|
| What does this system do and how do the pieces fit? | [architecture/overview.md](architecture/overview.md) |
| How does a comment become a posted answer? | [architecture/data-flow.md](architecture/data-flow.md) |
| Why did we choose PostgreSQL + pgvector? | [architecture/decisions/ADR-001-pgvector.md](architecture/decisions/ADR-001-pgvector.md) |
| Why Redis queues instead of Celery? | [architecture/decisions/ADR-002-redis-queues.md](architecture/decisions/ADR-002-redis-queues.md) |
| Why Gemini instead of OpenAI? | [architecture/decisions/ADR-003-gemini-not-openai.md](architecture/decisions/ADR-003-gemini-not-openai.md) |
| How does the FastAPI app start up? | [backend/overview.md](backend/overview.md) |
| How does JWT auth work? | [backend/auth.md](backend/auth.md) |
| How do WebSockets work? | [backend/websocket.md](backend/websocket.md) |
| What are all the config keys? | [backend/configuration.md](backend/configuration.md) |
| What do the workers do? | [workers/overview.md](workers/overview.md) |
| What are all the REST endpoints? | [api/rest.md](api/rest.md) |
| What WebSocket events are emitted? | [api/websocket-events.md](api/websocket-events.md) |
| What error codes exist? | [api/error-codes.md](api/error-codes.md) |
| What does the database look like? | [data/schema.md](data/schema.md) |
| How do I run a migration? | [data/migrations.md](data/migrations.md) |
| How does quota enforcement work? | [data/quota-model.md](data/quota-model.md) |
| What are the shared cross-platform types? | [data/shared-contracts.md](data/shared-contracts.md) |
| How does the React frontend work? | [frontend/overview.md](frontend/overview.md) |
| What does each component do? | [frontend/components.md](frontend/components.md) |
| How do the hooks work? | [frontend/state-and-hooks.md](frontend/state-and-hooks.md) |
| How does the API client work? | [frontend/api-client.md](frontend/api-client.md) |
| How does the Chrome extension work? | [chrome-extension/overview.md](chrome-extension/overview.md) |
| How do I start the system locally? | [infra/local-dev.md](infra/local-dev.md) |
| How do I deploy to production? | [infra/deployment.md](infra/deployment.md) |
| What are all the environment variables? | [infra/configuration-reference.md](infra/configuration-reference.md) |
| What Prometheus metrics are exported? | [observability/metrics.md](observability/metrics.md) |
| How is logging structured? | [observability/logging.md](observability/logging.md) |
| How does YouTube OAuth work? | [security/youtube-oauth.md](security/youtube-oauth.md) |
| What is the current project status? | [state/phase-status.md](state/phase-status.md) |
| What are the known bugs and tech debt? | [state/known-issues.md](state/known-issues.md) |
| Worker crashed — what do I do? | [state/runbooks/worker-crash.md](state/runbooks/worker-crash.md) |
| YouTube quota exceeded — what do I do? | [state/runbooks/youtube-quota-exceeded.md](state/runbooks/youtube-quota-exceeded.md) |

---

## Folder Summary

```
docs/
├── architecture/   — System design, data flow, scalability, ADRs (the "why")
├── backend/        — FastAPI app: auth, WebSocket, config, services
├── workers/        — Redis queue workers: each worker's payload and behavior
├── api/            — REST endpoints, WebSocket events, error codes (the "what")
├── data/           — DB schema, migrations, quota model, shared contracts
├── frontend/       — React 19 + Vite 7: components, hooks, API client
├── chrome-extension/ — Manifest V3 extension: background services, build
├── infra/          — Local dev, deployment, all env vars
├── observability/  — Metrics, logging, Grafana dashboards, alerting
├── security/       — JWT, CORS, YouTube OAuth, secrets
└── state/          — LIVING: phase status, known issues, operational runbooks
```

---

## Docs Conventions

- **One concept, one home.** Every other file cross-references by link. See [anti-duplication rules](architecture/overview.md#anti-duplication-rules).
- **ADRs are immutable once merged.** Add a superseding ADR rather than editing.
- **`state/` files are living documents.** Update them as the system evolves.
- **Runbook template:** Symptom → Detect → Respond → Root cause → Escalate. See [state/runbooks/README.md](state/runbooks/README.md).
- **Content population is separate from structure.** Placeholder files contain `> Purpose:` headers; fill content by consulting the [critical source files](architecture/overview.md#critical-source-files).

---

## All Files Index

Complete listing of every file in this docs repository:

**Architecture**
- [architecture/overview.md](architecture/overview.md) — Component map, design principles, anti-duplication rules
- [architecture/data-flow.md](architecture/data-flow.md) — 9-step comment → answer pipeline
- [architecture/scalability.md](architecture/scalability.md) — Horizontal scaling, WS sticky-session constraint
- [architecture/decisions/README.md](architecture/decisions/README.md) — ADR index + how to add a new ADR
- [architecture/decisions/ADR-001-pgvector.md](architecture/decisions/ADR-001-pgvector.md) — Why PostgreSQL + pgvector
- [architecture/decisions/ADR-002-redis-queues.md](architecture/decisions/ADR-002-redis-queues.md) — Why custom Redis sorted sets
- [architecture/decisions/ADR-003-gemini-not-openai.md](architecture/decisions/ADR-003-gemini-not-openai.md) — Why Gemini replaced OpenAI
- [architecture/decisions/ADR-004-rag-design.md](architecture/decisions/ADR-004-rag-design.md) — Why human approval before post
- [architecture/decisions/ADR-005-react-vite-frontend.md](architecture/decisions/ADR-005-react-vite-frontend.md) — Why React 19 + Vite 7

**Backend**
- [backend/overview.md](backend/overview.md) — FastAPI entrypoint, routers, middleware stack
- [backend/auth.md](backend/auth.md) — JWT lifecycle, bcrypt, token blacklist, refresh
- [backend/websocket.md](backend/websocket.md) — ConnectionManager, heartbeat, Redis pub/sub relay
- [backend/configuration.md](backend/configuration.md) — Every config key with defaults
- [backend/services.md](backend/services.md) — Gemini, RAG, YouTubeClient, quota, rate limiter

**Workers**
- [workers/overview.md](workers/overview.md) — QueueManager, retry, DLQ, runner.py
- [workers/classification.md](workers/classification.md) — ClassificationPayload → is_question
- [workers/embeddings.md](workers/embeddings.md) — EmbeddingPayload → 768-dim pgvector
- [workers/clustering.md](workers/clustering.md) — Cosine similarity at 0.65 → Cluster CRUD
- [workers/answer-generation.md](workers/answer-generation.md) — RAG + LLM → Answer record
- [workers/trigger-monitor.md](workers/trigger-monitor.md) — **Stub** (not implemented, not started by start_dev.sh)
- [workers/youtube-polling.md](workers/youtube-polling.md) — ThreadPoolExecutor, chat_id cache, dedup
- [workers/youtube-posting.md](workers/youtube-posting.md) — YouTubePostingPayload → YouTube API

**API**
- [api/rest.md](api/rest.md) — All REST endpoints: method, path, auth, schemas, errors
- [api/websocket-events.md](api/websocket-events.md) — All 14 event types with JSON payloads
- [api/error-codes.md](api/error-codes.md) — HTTP status semantics, error_code enum, WS 4001/4003

**Data**
- [data/schema.md](data/schema.md) — All 8 DB models: fields, types, constraints
- [data/migrations.md](data/migrations.md) — Alembic workflow: create, apply, rollback
- [data/quota-model.md](data/quota-model.md) — Application quota + YouTube API quota costs
- [data/shared-contracts.md](data/shared-contracts.md) — shared/ JSON schemas + TS constants

**Frontend**
- [frontend/overview.md](frontend/overview.md) — React 19 + Vite 7, routing, AuthProvider, dev/build
- [frontend/components.md](frontend/components.md) — All components: purpose + data needs
- [frontend/state-and-hooks.md](frontend/state-and-hooks.md) — useAuth, useWebSocket, useToast
- [frontend/api-client.md](frontend/api-client.md) — apiFetch helper, named service exports

**Chrome Extension**
- [chrome-extension/overview.md](chrome-extension/overview.md) — Manifest V3, permissions, background SW
- [chrome-extension/background-services.md](chrome-extension/background-services.md) — auth.ts, youtubePoller.ts, websocket.ts, quota.ts
- [chrome-extension/build-and-load.md](chrome-extension/build-and-load.md) — Build, load unpacked, dev vs prod

**Infrastructure**
- [infra/local-dev.md](infra/local-dev.md) — Docker Compose, ports, startup order, Makefile
- [infra/deployment.md](infra/deployment.md) — Terraform, Docker, HTTPS requirement, FRONTEND_DIR
- [infra/configuration-reference.md](infra/configuration-reference.md) — Master table of ALL env vars

**Observability**
- [observability/metrics.md](observability/metrics.md) — All Prometheus metrics with labels + PromQL
- [observability/logging.md](observability/logging.md) — Log levels, JSON format, RequestContextMiddleware
- [observability/dashboards.md](observability/dashboards.md) — 4 Grafana dashboards: panels, import
- [observability/alerting.md](observability/alerting.md) — prometheus/rules.yml, thresholds, incident checklist

**Security**
- [security/overview.md](security/overview.md) — JWT, CORS, ORM, rate limiting, quota enforcement
- [security/youtube-oauth.md](security/youtube-oauth.md) — Full OAuth flow, CSRF state, postMessage
- [security/secrets-management.md](security/secrets-management.md) — encrypt_data/decrypt_data, rotation

**State**
- [state/phase-status.md](state/phase-status.md) — LIVING: phases 1–4 complete, next priorities
- [state/known-issues.md](state/known-issues.md) — LIVING: active bugs, tech debt
- [state/runbooks/README.md](state/runbooks/README.md) — Runbook template, severity levels
- [state/runbooks/queue-overflow.md](state/runbooks/queue-overflow.md) — Detect, scale, drain, inspect DLQ
- [state/runbooks/worker-crash.md](state/runbooks/worker-crash.md) — Restart, DLQ review, root cause
- [state/runbooks/db-connection-loss.md](state/runbooks/db-connection-loss.md) — Health 503, reconnect, escalation
- [state/runbooks/youtube-quota-exceeded.md](state/runbooks/youtube-quota-exceeded.md) — 403 detection, pause, reset

---

## Legacy Files

The original 6 docs files are preserved in [`_archive/`](_archive/) during migration.
Their content is being distributed into the new structure per the [migration plan](architecture/overview.md#migration-plan).
