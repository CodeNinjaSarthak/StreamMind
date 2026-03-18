# Runbook: Database Connection Loss

**Severity:** P1 Critical
**Last updated:** 2026-03-01

## Symptom

- `GET /health` returns HTTP 503
- All API endpoints returning 500 errors
- Backend logs show `sqlalchemy.exc.OperationalError` or `psycopg2.OperationalError`
- Grafana: all panels showing "No data" or errors
- Workers failing and items accumulating in queues

## Detect

1. **Check health endpoint:**
   ```bash
   curl http://localhost:8000/health
   # Expected: {"status": "ok"}
   # Failing: {"status": "error", "detail": "database"} or 503
   ```

2. **Check backend logs** for DB connection errors:
   ```bash
   # Look for OperationalError, connection refused, timeout
   ```

3. **Test DB connectivity directly:**
   ```bash
   psql postgresql://user:password@localhost:5432/streammind_dev -c "SELECT 1;"
   ```

4. **Check PostgreSQL is running:**
   ```bash
   docker-compose ps postgres
   # or
   systemctl status postgresql
   ```

## Respond

1. **If PostgreSQL is down, restart it:**
   ```bash
   docker-compose up -d postgres
   # Wait for healthy:
   docker-compose ps
   ```

2. **Check PostgreSQL logs** for the reason it went down:
   ```bash
   docker-compose logs postgres --tail=100
   ```

3. **Verify `pool_pre_ping` is configured** in SQLAlchemy:
   - This setting validates connections before use, preventing stale connection errors
   - Check `backend/app/db/session.py`

4. **Backend should reconnect automatically** once PostgreSQL is available
   (SQLAlchemy connection pool with `pool_pre_ping=True` handles this).
   If not: restart the backend process.

5. **Check for DB disk space issues:**
   ```bash
   df -h
   ```

6. **Run any missed migrations** if the DB was reset:
   ```bash
   cd backend
   alembic upgrade head
   ```

## Root Cause

Common causes:
- PostgreSQL container crashed (OOM, disk full)
- Network partition between backend and DB
- DB credentials changed
- PostgreSQL max connections reached

## Escalate

If DB remains unavailable after 5 minutes:
- Escalate immediately (P1)
- Check cloud provider status if using managed DB (RDS, Cloud SQL)
- Include: health check output, DB logs, disk usage
