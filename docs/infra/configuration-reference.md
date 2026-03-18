# Configuration Reference

> Purpose: Master table of ALL environment variables across all services — backend, workers, and infra.

<!-- Populate from: backend/app/core/config.py, workers/common/config.py (verify), docker-compose.yml -->
<!-- This is the SINGLE source of truth for env var defaults. -->

## All Environment Variables

| Variable | Type | Default | Required | Services | Notes |
|----------|------|---------|----------|----------|-------|
| `DATABASE_URL` | str | — | Yes | backend, workers | PostgreSQL connection string |
| `SECRET_KEY` | str | — | Yes | backend | JWT signing; `openssl rand -hex 32` |
| `ALGORITHM` | str | `HS256` | No | backend | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30` | No | backend | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | `7` | No | backend | |
| `REDIS_URL` | str | `redis://localhost:6379` | No | backend, workers | |
| `GEMINI_API_KEY` | str | — | Yes | backend, workers | Google Gemini API key |
| `YOUTUBE_CLIENT_ID` | str | — | Yes (for YouTube) | backend | |
| `YOUTUBE_CLIENT_SECRET` | str | — | Yes (for YouTube) | backend | |
| `YOUTUBE_REDIRECT_URI` | str | — | Yes (for YouTube) | backend | Must match Google Console; HTTPS in prod |
| `FRONTEND_DIR` | str | `""` | No | backend | Path to frontend/dist/ |
| `CORS_ORIGINS` | str (comma-separated) | `http://localhost:5173,http://localhost:8080` | No | backend | |
| `LOG_LEVEL` | str | `INFO` | No | backend, workers | |
| `LOG_JSON` | bool | `False` | No | backend | Structured JSON logging |
| `ENCRYPTION_KEY` | str | — | Yes | backend | ≥32 chars; Fernet encryption for OAuth tokens |
| `ENVIRONMENT` | str | `development` | No | backend | "development", "staging", "production" |
| `DEBUG` | bool | `False` | No | backend | |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | int | `60` | No | backend | Per-IP rate limiting |
| `RATE_LIMIT_ENABLED` | bool | `True` | No | backend | |
| `PASSWORD_BCRYPT_ROUNDS` | int | `12` | No | backend | |
| `GEMINI_MODEL` | str | `gemini-2.5-flash` | No | workers | Classification + answer gen model |
| `GEMINI_EMBEDDING_MODEL` | str | `gemini-embedding-001` | No | workers | Embedding model |
| `CLASSIFICATION_CONFIDENCE_THRESHOLD` | float | `0.4` | No | workers | Min confidence for embedding queue |
| `CLUSTERING_SIMILARITY_THRESHOLD` | float | `0.65` | No | workers | pgvector cosine similarity cutoff |
| `DEFAULT_DAILY_ANSWER_LIMIT` | int | `100` | No | backend | Per-teacher daily answer limit |
| `DEFAULT_MONTHLY_SESSION_LIMIT` | int | `30` | No | backend | Per-teacher monthly session limit |
| `ENABLE_METRICS` | bool | `True` | No | backend, workers | Prometheus metrics |
| `METRICS_PORT` | int | `9090` | No | backend | |
| `WEBSOCKET_HEARTBEAT_INTERVAL` | int | `30` | No | backend | Seconds between heartbeats |
| `WEBSOCKET_TIMEOUT` | int | `300` | No | backend | Connection timeout in seconds |
| `MOCK_YOUTUBE` | bool | `False` | No | workers | Use mock YouTube polling |
| `DATABASE_POOL_SIZE` | int | `5` | No | backend | SQLAlchemy pool size |
| `DATABASE_MAX_OVERFLOW` | int | `10` | No | backend | SQLAlchemy max overflow |
| `REDIS_MAX_CONNECTIONS` | int | `10` | No | backend, workers | |
| `PROMETHEUS_MULTIPROC_DIR` | str | `/tmp/prometheus_multiproc` | No | backend, workers | Multiprocess metrics dir |

## Notes

- Variables marked "Yes (for YouTube)" are only required if YouTube integration is enabled
- `ENCRYPTION_KEY` is used to encrypt/decrypt YouTube OAuth tokens stored in DB
  See [security/secrets-management.md](../security/secrets-management.md)
- `CORS_ORIGINS` accepts a comma-separated list in production env vars; may be a Python
  list in `.env` files depending on the Pydantic Settings parser

## Per-Service Environment Files

| Service | File (dev) | Notes |
|---------|-----------|-------|
| Backend | `backend/.env.development` | Gitignored |
| Workers | Same or separate (verify) | |

## Secret Variables

Never commit to git:
- `DATABASE_URL` (contains password)
- `SECRET_KEY`
- `GEMINI_API_KEY`
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`
- `ENCRYPTION_KEY`

See [security/secrets-management.md](../security/secrets-management.md).
