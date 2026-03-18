# Local Development Setup

> Purpose: Docker Compose services, ports, volumes, startup order, and all `make` commands.

<!-- Populate from: docker-compose.yml, Makefile, docs/_archive/getting_started.md -->

## Prerequisites

- Docker + Docker Compose
- Python 3.13+
- Node.js 20+
- Redis (or via Docker)
- PostgreSQL (or via Docker)

## Docker Compose Services

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    ports: ["5432:5432"]
    volumes: [postgres_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  # Add other services as defined in docker-compose.yml
```

### Startup Order

```bash
# Start infrastructure only
docker-compose up -d postgres redis

# Run migrations
cd backend
DATABASE_URL=postgresql://user:password@localhost:5432/ai_doubt_manager_dev alembic upgrade head

# Start backend
cd backend
uvicorn app.main:app --reload --port 8000

# Start ALL services (backend + 6 workers + scheduler + frontend) via tmux
./start_dev.sh

# Start frontend
cd frontend
npm run dev   # → http://localhost:5173
```

## Ports

| Service | Port | URL |
|---------|------|-----|
| FastAPI backend | 8000 | http://localhost:8000 |
| React dev server | 5173 | http://localhost:5173 |
| PostgreSQL | 5432 | postgresql://localhost:5432 |
| Redis | 6379 | redis://localhost:6379 |
| Prometheus | 9090 | http://localhost:9090 |
| Grafana | 3000 | http://localhost:3000 |

## Makefile Commands

```bash
make run-backend   # uvicorn app.main:app --reload on :8000
make format        # Black + isort (line-length=119)
make lint          # Ruff + flake8 + pylint
make test          # pytest backend/tests workers -v
make test-coverage # Coverage report to HTML + terminal
make migrate       # alembic upgrade head
make migration MSG="..." # alembic revision --autogenerate
make downgrade     # alembic downgrade -1
make install       # pip install requirements for backend + workers
make clean         # Remove __pycache__, .pyc, .egg-info, .pytest_cache
```

## Environment Files

- Backend: `backend/.env.development` (copy from `backend/.env.example`)
- For all env vars, see [infra/configuration-reference.md](configuration-reference.md)

## YouTube OAuth (Local)

YouTube OAuth requires HTTPS in production, but localhost is allowed during development.
See [security/youtube-oauth.md](../security/youtube-oauth.md) for full OAuth setup.
See [docs/_archive/YOUTUBE_SETUP.md](../_archive/YOUTUBE_SETUP.md) for the original Google Console setup guide.
