# Architecture Overview

> Purpose: System purpose, component inventory, and design principles — the "what" before the "why".

<!-- Populate from: docs/_archive/architecture.md (Components section) -->

## System Purpose

AI Live Doubt Manager helps teachers manage live YouTube teaching sessions at scale. It polls the YouTube live chat in real time, uses Gemini AI to classify and cluster student questions, generates RAG-augmented answers, and delivers them back to the teacher's dashboard over WebSocket — with optional posting directly to the YouTube stream.

**Users:** Teachers running live YouTube educational sessions.
**Problem:** Live chat during popular sessions becomes an unreadable flood. Genuine student questions get buried. Teachers cannot respond to questions at scale.

## Component Inventory

| Component | Technology | Location |
|-----------|-----------|----------|
| Backend API | FastAPI (Python 3.13), uvicorn | `backend/app/` |
| PostgreSQL | PostgreSQL 15 + pgvector extension | Docker or native |
| Redis | Redis 7 | Docker or native |
| Worker Pipeline | 6 independent Python processes + scheduler | `workers/` |
| Frontend SPA | React 19, Vite 7, Recharts | `frontend/src/` |
| Chrome Extension | TypeScript, Manifest V3 | `chrome-extension/` |
| AI Services | Google Gemini (gemini-2.5-flash, gemini-embedding-001) | Via API |
| Observability | Prometheus metrics, structured logging | `backend/app/core/metrics.py` |

## Design Principles

1. **Decouple ingress from processing** — Redis queues separate API/polling from AI work, allowing each stage to fail independently
2. **Ownership-first data access** — Every query JOINs to StreamingSession and filters `teacher_id == current_user.id`
3. **Real-time without coupling** — Workers publish to Redis pub/sub; the API relays to WebSocket clients. Workers never hold WS connections
4. **Online over batch** — Nearest-centroid clustering processes each question as it arrives, no batch re-processing
5. **Fail to queue, not to void** — Tasks persist in Redis ZSET until consumed; DLQ captures exhausted retries

## Anti-Duplication Rules

Each concept has exactly one canonical home. All other files cross-reference by link.

| Concept | Lives in | Does NOT live in |
|---------|----------|-----------------|
| WebSocket event JSON payloads | `api/websocket-events.md` | backend/websocket.md, workers/*.md |
| DB model field definitions | `data/schema.md` | backend/overview.md, workers/*.md |
| REST endpoint request/response schemas | `api/rest.md` | frontend/api-client.md, backend/*.md |
| All env var defaults | `infra/configuration-reference.md` | infra/local-dev.md, backend/configuration.md |
| Quota cost table | `data/quota-model.md` | workers/youtube-posting.md, workers/youtube-polling.md |
| Prometheus metric definitions | `observability/metrics.md` | observability/alerting.md, state/runbooks/*.md |
| ADR rationale | `architecture/decisions/ADR-*.md` | data/schema.md, workers/overview.md |
| OAuth CSRF flow details | `security/youtube-oauth.md` | backend/auth.md, infra/deployment.md |
| Setup commands | `infra/local-dev.md` | state/runbooks/*.md (emergency inline only) |
| Shared cross-platform types | `data/shared-contracts.md` | chrome-extension/background-services.md, api/*.md |

## Critical Source Files

Files to consult when populating content:

| Doc File | Source File |
|----------|-------------|
| `backend/configuration.md`, `infra/configuration-reference.md` | `backend/app/core/config.py` |
| `workers/overview.md` | `workers/common/queue.py` |
| `api/websocket-events.md` | `backend/app/services/websocket/` |
| `data/schema.md` | `backend/app/db/models/` |
| `api/rest.md` | `backend/app/api/v1/` |
| `observability/alerting.md` | `infra/prometheus/rules.yml` |
| `observability/metrics.md` | `backend/app/core/metrics.py` |
| `data/shared-contracts.md` | `shared/` directory |

## Migration Plan

The original 6 docs files map to this new structure:

| Original File | Destination |
|--------------|-------------|
| `architecture.md` | Components → here; data-flow → `data-flow.md`; DB → `data/schema.md`; scalability → `scalability.md`; security → `security/overview.md`; phase status → `state/phase-status.md` |
| `getting_started.md` | Docker/setup → `infra/local-dev.md`; env vars → `infra/configuration-reference.md`; monitoring → `observability/dashboards.md`; troubleshooting → `state/runbooks/*.md` |
| `api_contracts.md` | REST → `api/rest.md`; WebSocket events → `api/websocket-events.md`; errors → `api/error-codes.md` |
| `failure_modes.md` | Per-failure sections → `state/runbooks/*.md`; metrics → `observability/alerting.md`; logging → `observability/logging.md`; Grafana → `observability/dashboards.md`; checklist → `state/runbooks/README.md` |
| `quota_model.md` | → `data/quota-model.md` |
| `YOUTUBE_SETUP.md` | Cloud setup → `security/youtube-oauth.md`; env vars → `infra/local-dev.md`; prod HTTPS → `infra/deployment.md`; quota → `data/quota-model.md`; troubleshooting → `state/runbooks/youtube-quota-exceeded.md` |
