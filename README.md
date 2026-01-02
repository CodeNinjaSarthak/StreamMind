# AI Live Doubt Manager System

A production-grade system for managing live doubt sessions with YouTube integration.

## Project Structure

```
ai-live-doubt-manager/
├── backend/          # FastAPI backend application
├── workers/          # Async background workers
├── chrome-extension/ # Chrome extension overlay
├── shared/           # Shared schemas and constants
├── infra/            # Infrastructure as code
├── scripts/           # Utility scripts
└── docs/             # Documentation
```

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL
- Redis
- Node.js (for Chrome extension)

### Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Install dependencies:
   ```bash
   make install
   ```

### Running the Backend

```bash
make run-backend
```

Or directly:
```bash
uvicorn backend.app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Running Workers

```bash
make run-workers
```

Or run individual workers:
```bash
python -m workers.classification.worker
python -m workers.embeddings.worker
python -m workers.clustering.worker
python -m workers.answer_generation.worker
python -m workers.trigger_monitor.worker
```

### Docker Compose

Run the entire stack:
```bash
docker-compose up
```

## Development

### Code Formatting

```bash
make format
```

### Linting

```bash
make lint
```

### Testing

```bash
make test
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/sessions` - List sessions
- `WS /ws/{session_id}` - WebSocket connection

All endpoints currently return `{"status": "ok"}` as stubs.

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed architecture documentation.

## License

MIT

