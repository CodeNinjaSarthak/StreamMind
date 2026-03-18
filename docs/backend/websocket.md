# WebSocket

> Purpose: ConnectionManager, heartbeat protocol, Redis pub/sub relay, and the 14 event types.

<!-- Populate from: backend/app/services/websocket/, backend/app/main.py -->

## ConnectionManager

Located in `backend/app/services/websocket/manager.py` (verify path).

Responsibilities:
- Accept and register WebSocket connections keyed by `(session_id, user_id)`
- Broadcast events to all connections for a session
- Handle disconnection cleanup

## Authentication

WebSocket auth uses a first-message pattern. After connecting to `/ws/{session_id}`:
1. Client sends `{"type": "auth", "token": "<jwt>"}` as the first message
2. Backend validates JWT signature, checks blacklist, and verifies session ownership
3. An optional `?token=` query parameter is also supported

- Close code `4001`: invalid/expired token or missing auth message
- Close code `4003`: valid token but session not owned by this user

## Heartbeat

<!-- Heartbeat interval, ping/pong protocol, timeout behavior -->

## Redis Pub/Sub Relay

`_relay_redis_events()` in `backend/app/main.py`:
- Subscribes to pattern `ws:session:{id}` on startup
- Workers publish to `ws:session:{session_id}` with JSON payloads
- Relay deserializes and broadcasts to all WebSocket clients for that session

This decouples workers (which don't hold WS connections) from the backend instances
that do. See [architecture/scalability.md](../architecture/scalability.md) for the
sticky-session constraint this implies.

## Event Types

All 14 event types with exact JSON payloads are documented in:
**[api/websocket-events.md](../api/websocket-events.md)**

Do not duplicate event payload definitions here.
