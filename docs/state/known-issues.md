# Known Issues

> **LIVING DOCUMENT** — Update when bugs are found or resolved.
> Last updated: 2026-03-18

## Active Bugs

<!-- Format: [SEVERITY] Description — workaround if any -->

| ID | Severity | Description | Workaround | File |
|----|---------|-------------|-----------|------|
| — | — | No known active bugs at time of doc structure creation | — | — |

## Tech Debt

| ID | Area | Description | Impact |
|----|------|-------------|--------|
| TD-001 | Frontend | ~~ActivityLog and AnalyticsPanel stubs~~ **Resolved** — both are fully implemented | — |
| TD-002 | Workers | No built-in monitoring UI for queue depths or DLQ contents | Medium — must use redis-cli to inspect |
| TD-003 | Migrations | Some migrations written manually (no Docker in dev environment) | Low — documented in data/migrations.md |
| TD-004 | Tests | <!-- Coverage of workers/youtube integration --> | <!-- impact --> |

## Missing Implementations

| Feature | Notes |
|---------|-------|
| <!-- feature --> | <!-- what's needed --> |

## Workarounds

| Issue | Workaround |
|-------|-----------|
| No Celery Flower equivalent | Use `redis-cli ZCARD {queue_name}` to check queue depths |

## Resolved Issues

<!-- Move items here when fixed, with date and fix description -->

| ID | Description | Fixed in | Date |
|----|-------------|---------|------|
| — | — | — | — |
