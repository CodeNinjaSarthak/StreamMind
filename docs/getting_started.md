# Getting Started

This guide will help you set up and run the AI Live Doubt Manager system locally for development.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** - Backend and workers
- **PostgreSQL 15+** with **pgvector** extension - Database with vector similarity search
- **Redis 7+** - Message queue and caching
- **Node.js 18+** and **npm** - Chrome extension development
- **Docker & Docker Compose** (Recommended) - Simplified setup
- **Google Cloud Account** - For YouTube API credentials

---

## Quick Start with Docker Compose (Recommended)

The fastest way to get started is using Docker Compose, which sets up all services automatically.

### 1. Clone Repository

```bash
git clone <repository-url>
cd agentic
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env.development
```

Edit `.env.development` and configure the following critical values:

**Required Settings:**
```bash
# Security - IMPORTANT: Generate a strong secret key
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# YouTube API - Get from Google Cloud Console
YOUTUBE_CLIENT_ID=your-youtube-client-id
YOUTUBE_CLIENT_SECRET=your-youtube-client-secret
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/v1/youtube/auth/callback
```

**Generate Secret Key:**
```bash
openssl rand -hex 32
```

**Note:** When using Docker Compose, DATABASE_URL and REDIS_URL are pre-configured in `docker-compose.yml`.

### 3. Start All Services

```bash
docker-compose up
```

This starts:
- **PostgreSQL** (port 5432) with pgvector extension
- **Redis** (port 6379)
- **API Backend** (port 8000)
- **Workers** (background processing)

### 4. Verify Setup

Check that services are running:

```bash
# API health check
curl http://localhost:8000/health
# Should return: {"status":"ok","health":"healthy"}

# API documentation
open http://localhost:8000/docs
```

**You're ready!** Skip to [First Session](#first-session) section.

---

## Manual Setup (Alternative)

For more control or development without Docker, follow these steps.

### 1. Clone Repository

```bash
git clone <repository-url>
cd agentic
```

### 2. Install PostgreSQL 15+ with pgvector

**macOS (Homebrew):**
```bash
brew install postgresql@15
brew services start postgresql@15

# Install pgvector
brew install pgvector
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install postgresql-15 postgresql-15-pgvector
sudo systemctl start postgresql
```

**Create Database:**
```bash
psql postgres
CREATE DATABASE ai_doubt_manager;
CREATE EXTENSION vector;
\q
```

### 3. Install Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### 4. Configure Environment

```bash
cp .env.example .env.development
```

Edit `.env.development` with your local configuration:

```bash
# Application
ENVIRONMENT=development
DEBUG=true

# Database - Update with your PostgreSQL credentials
DATABASE_URL=postgresql://user:password@localhost:5432/ai_doubt_manager

# Redis
REDIS_URL=redis://localhost:6379/0

# Security - IMPORTANT: Generate strong secret key
SECRET_KEY=<run: openssl rand -hex 32>

# YouTube API - From Google Cloud Console
YOUTUBE_CLIENT_ID=your-client-id
YOUTUBE_CLIENT_SECRET=your-client-secret
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/v1/youtube/auth/callback

# Logging
LOG_LEVEL=DEBUG
LOG_JSON=false
```

### 5. Install Python Dependencies

```bash
# Using Makefile (recommended)
make install

# Or manually
pip install -r backend/requirements.txt
pip install -r workers/requirements.txt
```

**Dependencies include:**
- FastAPI, Uvicorn - Web framework
- SQLAlchemy, Alembic - Database ORM and migrations
- Redis, Celery - Task queue
- Pydantic - Data validation
- pytest - Testing
- black, ruff, flake8 - Code quality

### 6. Run Database Migrations

Create all database tables (teachers, streaming_sessions, comments, clusters, answers, quotas, youtube_tokens, rag_documents):

```bash
# Using Makefile
make migrate

# Or manually
cd backend && alembic upgrade head
```

**Verify tables were created:**
```bash
psql ai_doubt_manager -c "\dt"
```

### 7. Run the System

You need to run the backend API and workers in separate terminals.

**Terminal 1 - Backend API:**
```bash
make run-backend

# Or manually:
# cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Workers:**
```bash
make run-workers

# Or run individual workers:
# python -m workers.classification.worker
# python -m workers.embeddings.worker
# python -m workers.clustering.worker
# python -m workers.answer_generation.worker
# python -m workers.trigger_monitor.worker
```

### 8. Verify Setup

```bash
# Backend running
curl http://localhost:8000
# Returns: {"app_name":"AI Live Doubt Manager","version":"1.0.0",...}

# Health check
curl http://localhost:8000/health
# Returns: {"status":"ok","health":"healthy"}

# API Documentation
open http://localhost:8000/docs
```

---

## Chrome Extension Setup

### 1. Install Node.js Dependencies

```bash
cd chrome-extension
npm install
```

### 2. Build Extension

```bash
npm run build
```

This creates a `dist/` folder with the compiled extension.

### 3. Load in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer Mode** (toggle in top-right)
3. Click **"Load unpacked"**
4. Select the `chrome-extension/dist` folder
5. Extension icon should appear in Chrome toolbar

### 4. Configure Extension

1. Click the extension icon in Chrome toolbar
2. Dashboard opens in a popup/side panel
3. Click **"Login"** and enter teacher credentials (see [First Session](#first-session))
4. Authenticate with YouTube (if prompted)
5. Extension is now ready to use on YouTube Live videos

---

## First Session

Let's create a teacher account and start a session.

### 1. Create Teacher Account

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@example.com",
    "password": "SecurePass123",
    "name": "Test Teacher"
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "teacher@example.com",
  "name": "Test Teacher",
  "is_active": true,
  "is_verified": false
}
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teacher@example.com",
    "password": "SecurePass123"
  }'
```

**Response:** Copy the `access_token` from the response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 3. Use the Extension

1. Navigate to a YouTube Live video: `https://www.youtube.com/watch?v=<video_id>`
2. Chrome extension detects the live video
3. Dashboard shows:
   - Active session status
   - Live comments streaming in
   - Questions being classified
   - Clusters forming
   - AI-generated answers

4. As questions come in:
   - Comments are classified (is_question: true/false)
   - Questions are embedded and clustered
   - AI generates answers for clusters
   - You can review and post answers back to YouTube

---

## Development Workflow

### Code Formatting

Format code with Black and isort:

```bash
make format
```

This formats all Python code in `backend/`, `workers/`, and `scripts/` with:
- Line length: 119 characters
- Black code style
- isort for import sorting

### Linting

Run all linters:

```bash
make lint
```

Runs:
- **ruff** - Fast Python linter
- **flake8** - Style guide enforcement
- **pylint** - Code analysis

### Testing

```bash
# Run all tests
make test

# Run with coverage report
make test-coverage
```

Tests are located in:
- `backend/tests/` - Backend API tests
- `workers/tests/` - Worker tests (if exists)

### Database Migrations

When you modify database models in `backend/app/db/models/`:

**Create a new migration:**
```bash
make migration MSG="add new field to comments"

# Or manually:
# cd backend && alembic revision --autogenerate -m "add new field to comments"
```

**Apply migrations:**
```bash
make migrate

# Or manually:
# cd backend && alembic upgrade head
```

**Rollback last migration:**
```bash
make downgrade

# Or manually:
# cd backend && alembic downgrade -1
```

**View migration history:**
```bash
cd backend && alembic history
```

### Clean Generated Files

Remove `__pycache__`, `*.pyc`, and test artifacts:

```bash
make clean
```

---

## Monitoring & Observability

### Viewing Logs

**Docker Compose:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f workers

# Last 100 lines
docker-compose logs --tail=100 api
```

**Manual Setup:**
- Backend logs: stdout (terminal where you ran `make run-backend`)
- Worker logs: stdout (terminal where you ran `make run-workers`)

**Production Logs:**
Set `LOG_JSON=true` in environment for structured JSON logging:
```json
{"timestamp":"2025-12-31T10:00:00.000Z","level":"INFO","message":"Server started","request_id":"abc123"}
```

### Prometheus Metrics

If Prometheus is configured (via Docker or manual setup):

**Access Prometheus:**
```bash
open http://localhost:9090
```

**Available Metrics:**
- `http_requests_total` - HTTP request count by endpoint/method/status
- `http_request_duration_seconds` - Request latency
- `websocket_connections_active` - Active WebSocket connections
- `queue_size_total` - Queue backlog by queue name
- `worker_heartbeat` - Worker health heartbeat
- `quota_usage` - Quota consumption by teacher/type

**Scrape Backend Metrics:**
```bash
curl http://localhost:8000/metrics
```

### Grafana Dashboards

If Grafana is configured:

```bash
open http://localhost:3000
# Default login: admin/admin
```

**Import Dashboards:**
- Dashboards are in `grafana/dashboards/` directory
- Import JSON files via Grafana UI

**Available Dashboards:**
- **API Performance** - Request rates, latencies, error rates
- **Worker Health** - Queue sizes, processing rates, heartbeats
- **Quota Usage** - Per-teacher quota consumption over time
- **Session Metrics** - Active sessions, comment volumes, cluster counts

---

## Troubleshooting

### Database connection refused

**Symptom:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solutions:**
```bash
# Docker: Check PostgreSQL container is running
docker-compose ps postgres

# Manual: Check PostgreSQL service
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Verify DATABASE_URL in .env matches your setup
# Docker: postgresql://user:password@postgres:5432/ai_doubt_manager
# Manual: postgresql://user:password@localhost:5432/ai_doubt_manager
```

### Redis connection timeout

**Symptom:** `redis.exceptions.ConnectionError: Error connecting to Redis`

**Solutions:**
```bash
# Docker: Check Redis container
docker-compose ps redis

# Manual: Check Redis service
brew services list  # macOS
sudo systemctl status redis  # Linux

# Test Redis connection
redis-cli ping
# Should return: PONG

# Verify REDIS_URL in .env
# Docker: redis://redis:6379/0
# Manual: redis://localhost:6379/0
```

### Workers not processing

**Symptom:** Comments received but not classified/clustered

**Solutions:**
```bash
# Check worker logs
docker-compose logs workers  # Docker
# Or check terminal where workers are running

# Verify Redis queue has items
redis-cli
LLEN classification
LLEN embedding
LLEN clustering

# Check worker_heartbeat metric
curl http://localhost:8000/metrics | grep worker_heartbeat
```

### Extension not connecting

**Symptom:** Chrome extension shows "Disconnected" or "Reconnecting..."

**Solutions:**
1. **Check Backend WebSocket:**
   ```bash
   # Test WebSocket endpoint
   # wscat -c ws://localhost:8000/ws/<session_id>
   ```

2. **Verify CORS Settings:**
   - Check `CORS_ORIGINS` in `.env` includes extension origin
   - Example: `CORS_ORIGINS=http://localhost:3000,chrome-extension://*`

3. **Check Browser Console:**
   - Open Chrome DevTools (F12)
   - Look for WebSocket errors or CORS errors

4. **Reload Extension:**
   - Go to `chrome://extensions/`
   - Click reload icon on AI Live Doubt Manager extension

### YouTube API quota exceeded

**Symptom:** `403 Forbidden` with `quotaExceeded` error from YouTube API

**Solutions:**
1. **Check Quota Usage:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to APIs & Services → Dashboard
   - View YouTube Data API v3 quota usage

2. **Quota Resets:**
   - YouTube quotas reset daily at midnight Pacific Time
   - Wait for reset or request quota increase from Google

3. **Reduce Polling Frequency:**
   - Modify polling interval in Chrome extension settings (when implemented)
   - Current default: polls every 5 seconds during active session

### Port already in use

**Symptom:** `OSError: [Errno 48] Address already in use`

**Solutions:**
```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Migration conflicts

**Symptom:** `alembic.util.exc.CommandError: Target database is not up to date`

**Solutions:**
```bash
# View current migration status
cd backend && alembic current

# View migration history
alembic history

# If conflicts exist, resolve manually or reset:
# WARNING: This drops all data
dropdb ai_doubt_manager
createdb ai_doubt_manager
psql ai_doubt_manager -c "CREATE EXTENSION vector;"
alembic upgrade head
```

---

## Next Steps

Now that your development environment is set up:

1. **Read Architecture Documentation:**
   - [Architecture Overview](./architecture.md) - Understand system design
   - [API Contracts](./api_contracts.md) - Learn API endpoints and schemas
   - [Quota Model](./quota_model.md) - Understand rate limiting

2. **Explore the Codebase:**
   - `backend/app/db/models/` - Database schema (8 models)
   - `backend/app/api/v1/` - API endpoints
   - `workers/` - Background processing pipeline
   - `shared/` - Shared contracts and constants

3. **Implement AI Features (Phase 2):**
   - Classification Worker - Integrate AI model for question classification
   - Embeddings Worker - Connect to OpenAI API for embeddings
   - Clustering Worker - Implement cosine similarity clustering
   - Answer Generation Worker - Build RAG-based answer generation

4. **Build YouTube Integration (Phase 3):**
   - Complete OAuth flow
   - Implement live chat polling
   - Add answer posting functionality

5. **Complete Chrome Extension (Phase 4):**
   - Build React dashboard UI
   - Implement real-time WebSocket client
   - Add quota monitoring and alerts

---

## Common Development Commands

```bash
# Start development
docker-compose up                   # All services
make run-backend                    # Backend only
make run-workers                    # Workers only

# Code quality
make format                         # Format code
make lint                           # Run linters
make test                           # Run tests
make test-coverage                  # Tests with coverage

# Database
make migrate                        # Run migrations
make migration MSG="description"    # Create migration
make downgrade                      # Rollback migration

# Utilities
make install                        # Install dependencies
make clean                          # Clean generated files
make help                           # Show all commands
```

---

## Environment Variables Reference

See `.env.example` for all available configuration options.

**Key Settings:**

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | `development` | Environment: development/staging/production |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `SECRET_KEY` | `change-me` | JWT secret (MUST change in production) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token expiry |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token expiry |
| `DEFAULT_DAILY_ANSWER_LIMIT` | `100` | Daily answer generation quota |
| `DEFAULT_MONTHLY_SESSION_LIMIT` | `30` | Monthly session quota |
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG/INFO/WARNING/ERROR |
| `LOG_JSON` | `false` | Enable JSON structured logging |
| `WEBSOCKET_HEARTBEAT_INTERVAL` | `30` | WebSocket ping interval (seconds) |

---

## Support

For issues or questions:
- Check troubleshooting section above
- Review documentation in `docs/` folder
- Check application logs for error details
- Verify all prerequisites are properly installed

---

**Reference Files:**
- Configuration: `.env.example`, `backend/app/core/config.py`
- Database Setup: `backend/app/db/session.py`, `backend/alembic/`
- Docker: `docker-compose.yml`, `infra/docker/`
- Makefile: `Makefile` (all development commands)
