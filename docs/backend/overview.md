# Backend Overview

> Purpose: FastAPI entrypoint, router list, middleware stack, and key dependency functions.

<!-- Populate from: backend/app/main.py, backend/app/api/v1/ -->

## Entrypoint

`backend/app/main.py` — FastAPI app with lifespan context manager.

### Lifespan Sequence
1. Clear stale Prometheus multiprocess metric files from `PROMETHEUS_MULTIPROC_DIR`
2. `manager.start_subscriber()` — background task subscribes to Redis `ws:session:*` channels for WebSocket relay
3. On shutdown: cancel relay task, log shutdown

## Router List

| Prefix | Module | Description |
|--------|--------|-------------|
| `/api/v1/auth` | `backend/app/api/v1/auth.py` | Register, login, refresh, logout |
| `/api/v1/sessions` | `backend/app/api/v1/sessions.py` | Session CRUD |
| `/api/v1/dashboard` | `backend/app/api/v1/dashboard.py` | Manual question, approve, edit, stats |
| `/api/v1/youtube` | `backend/app/api/v1/youtube.py` | YouTube OAuth + video validation |
| `/api/v1/rag` | `backend/app/api/v1/rag.py` | RAG document upload/list/delete |
| `/api/v1/comments` | `backend/app/api/v1/comments.py` | Comment get/mark answered |
| `/api/v1/clusters` | `backend/app/api/v1/clusters.py` | Cluster get/update/comments |
| `/api/v1/answers` | `backend/app/api/v1/answers.py` | Answer CRUD + post |
| `/api/v1/metrics` | `backend/app/api/v1/metrics.py` | Teacher-scoped metrics |
| `/ws` | `backend/app/api/v1/websocket.py` | WebSocket real-time events |

Full endpoint specs: [api/rest.md](../api/rest.md)

## Middleware Stack

Execution order (outermost middleware runs first on request):

1. **RateLimitMiddleware** — Redis-backed IP throttling (60 req/min default). Skips `/health`, `/metrics`, `/docs`.
2. **RequestContextMiddleware** — Injects `X-Request-ID`, tracks request duration, records Prometheus metrics.
3. **CORSMiddleware** — Configured origins from `CORS_ORIGINS` setting (includes `:5173` for Vite dev).

## Key Dependencies

| Dependency | Import | Purpose |
|------------|--------|---------|
| `get_db` | `backend/app/db/session.py` | SQLAlchemy session per request |
| `get_current_active_user` | `backend/app/core/security.py` | JWT auth, raises 401/403 |
| <!-- add more --> | | |

## Static Files Mount

When `settings.frontend_dir` is set, FastAPI mounts `frontend/dist/` at `/app` via
`StaticFiles`. The SPA catch-all serves `index.html` for unknown paths.
See [ADR-005](../architecture/decisions/ADR-005-react-vite-frontend.md).
