# Scalability

> Purpose: Which layers scale horizontally, the WebSocket sticky-session constraint, and pgvector at scale.

<!-- Populate from: docs/_archive/architecture.md (scalability section) -->

## Horizontal Scaling

| Layer | Scales Horizontally? | Notes |
|-------|---------------------|-------|
| FastAPI backend | Yes (with constraint) | WebSocket sticky sessions required — see below |
| Redis workers | Yes | Stateless; add workers per queue independently |
| PostgreSQL | Vertical + read replicas | pgvector queries on `embedding` column |
| Redis | Yes (cluster mode) | Shared state for queues, pub/sub, quota, OAuth |

## WebSocket Sticky-Session Constraint

<!-- Why WebSocket connections require sticky sessions; how Redis pub/sub relay mitigates this -->

The `_relay_redis_events()` background task in `backend/app/main.py` subscribes to
`ws:session:{id}` channels. Workers publish to Redis; the backend relays to connected
WebSocket clients. This means:

- A client connected to backend instance A receives events even if the worker that
  processed their comment ran on a different machine.
- However, **the WebSocket connection itself must be sticky** — load balancers must
  route a client's WS connection to the same backend instance for the lifetime of the
  connection.
- Recommended: use IP hash or cookie-based affinity in your load balancer config.

See [infra/deployment.md](../infra/deployment.md) for load balancer configuration.

## pgvector at Scale

<!-- Indexing strategy for 768-dim vectors; approximate nearest neighbor options -->

Current indexing: HNSW indexes on all three vector columns (`comments.embedding`, `clusters.centroid_embedding`, `rag_documents.embedding`) using `vector_cosine_ops` with tuning parameters `m=16, ef_construction=64`.

At current scale (hundreds to low thousands of comments per session), HNSW handles queries efficiently. At O(10K+) clusters per session, monitor query latency and consider increasing `ef_search` or partitioning by session.

## Queue Scaling

<!-- Per-queue worker scaling; DLQ overflow handling. See workers/overview.md -->
See [workers/overview.md](../workers/overview.md) for queue mechanics.
