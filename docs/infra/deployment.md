# Deployment

> Purpose: Terraform modules, Docker images, HTTPS requirement for YouTube OAuth, and FRONTEND_DIR in production.

<!-- Populate from: infra/ directory, docker-compose.prod.yml (if exists) -->

## Requirements

- **HTTPS is required** for YouTube OAuth in production. The redirect URI registered
  in Google Cloud Console must be an HTTPS URL. See [security/youtube-oauth.md](../security/youtube-oauth.md).
- PostgreSQL with pgvector extension enabled
- Redis
- All env vars set — see [infra/configuration-reference.md](configuration-reference.md)

## FRONTEND_DIR

Set `FRONTEND_DIR` to the path of the built frontend (`frontend/dist/`) so FastAPI
serves the React SPA via StaticFiles:

```bash
FRONTEND_DIR=/app/frontend/dist
```

FastAPI will:
1. Mount `StaticFiles` at `/app` pointing to `FRONTEND_DIR`
2. Serve `index.html` as the SPA catch-all for unknown paths

## Docker Images

<!-- Document Dockerfile locations and image names -->

| Service | Dockerfile | Image |
|---------|-----------|-------|
| Backend | `infra/docker/api.Dockerfile` | `ai-doubt-manager-backend` |
| Workers | `infra/docker/worker.Dockerfile` | `ai-doubt-manager-workers` |

## Terraform

<!-- If Terraform is used, document module structure and key resources -->

```
infra/
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
│       ├── vpc/
│       ├── database/
│       └── compute/
```

## Load Balancer Configuration

WebSocket connections require sticky sessions (IP hash or cookie affinity).
See [architecture/scalability.md](../architecture/scalability.md#websocket-sticky-session-constraint).

## Production Checklist

- [ ] HTTPS configured with valid TLS certificate
- [ ] `SECRET_KEY` set to a random 32-byte hex value (`openssl rand -hex 32`)
- [ ] YouTube OAuth redirect URI updated to production HTTPS URL
- [ ] `FRONTEND_DIR` set correctly
- [ ] `CORS_ORIGINS` updated for production domain
- [ ] Database migrations applied
- [ ] pgvector extension enabled
- [ ] All worker processes running
- [ ] Prometheus + Grafana configured
