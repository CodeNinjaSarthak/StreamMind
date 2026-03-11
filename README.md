# AI Powered Live Doubt Manager

A production-grade system that helps teachers manage live YouTube teaching sessions at scale. It polls the YouTube live chat in real time, uses Gemini AI to classify and cluster student questions, generates answers, and delivers them back to the teacher's dashboard over WebSocket — all while optionally posting responses directly into the stream.

## Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python), PostgreSQL + pgvector, Redis |
| AI Pipeline | Google Gemini (classification, embeddings, answer generation) |
| Workers | Redis queue workers (classification, embeddings, clustering, answer generation, YouTube polling/posting) |
| Frontend | React 19 + Vite, served by FastAPI |
| Browser | Chrome extension (TypeScript + Vite) |
| Infrastructure | Docker Compose (local), Terraform (cloud), Prometheus + Grafana (observability) |

## Architecture

```
YouTube Live Chat
      │
      ▼
youtube_polling worker  ──► Redis queue
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
            classification  embeddings  (retry/DLQ)
                    │           │
                    ▼           ▼
                 Gemini AI   pgvector
                    │           │
                    └─────┬─────┘
                          ▼
                    clustering worker
                          │
                          ▼
               answer_generation worker
                    │           │
                    ▼           ▼
            WebSocket push   youtube_posting worker
                    │               │
                    ▼               ▼
            Teacher dashboard   YouTube Live Chat
```

Comments flow from YouTube → Redis workers → Gemini AI for classification and embedding → pgvector for semantic clustering → answer generation → real-time WebSocket delivery to the teacher dashboard (and optionally back to the stream).

## Quick Start

### Prerequisites

- Docker and Docker Compose
- A `.env` file (see below)

### 1. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Random secret for JWT signing |
| `GEMINI_API_KEY` | Google Gemini API key |
| `YOUTUBE_CLIENT_ID` | Google OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | Google OAuth client secret |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |

See `.env.example` for the full list of supported variables and their defaults.

### 2. Run the stack

```bash
docker-compose up
```

This starts PostgreSQL, Redis, the FastAPI backend, and all workers. The API is available at `http://localhost:8000`.

### 3. Run database migrations

```bash
cd backend && alembic upgrade head
```

## Running Without Docker

**Backend:**
```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

**Workers:**
```bash
python -m workers.classification.worker
python -m workers.embeddings.worker
python -m workers.clustering.worker
python -m workers.answer_generation.worker
python -m workers.trigger_monitor.worker
```

**Chrome extension:**
```bash
cd chrome-extension && npm install && npm run build
```
Load `chrome-extension/dist` as an unpacked extension in Chrome.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/auth/login` | Authenticate, returns JWT |
| `GET` | `/api/v1/sessions` | List teacher's sessions |
| `POST` | `/api/v1/sessions` | Create a new session |
| `GET` | `/api/v1/clusters` | List question clusters for a session |
| `POST` | `/api/v1/dashboard/approve` | Approve an AI-generated answer |
| `GET` | `/api/v1/youtube/auth/url` | Start YouTube OAuth flow |
| `WS` | `/ws/{session_id}` | Real-time event stream |

Full API docs available at `http://localhost:8000/docs` when running.

## Development

```bash
make format   # auto-format
make lint     # run linters
make test     # run tests
```

## License

MIT
