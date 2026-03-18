"""Black-box contract tests for the WebSocket endpoint.

WebSocket path: /ws/{session_id}
Auth: first message must be JSON {"type": "auth", "token": "<jwt>"}
Close codes: 4001 (auth required / invalid token), 4003 (forbidden — wrong owner)

Uses Starlette's TestClient for WebSocket since httpx does not support WS upgrade.

Note: The WS handler uses SessionLocal() directly (not dependency injection),
so we patch app.api.v1.websocket.SessionLocal to return a test DB session.
"""

import uuid
from unittest.mock import patch

import pytest
from app.main import app
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from tests.conftest import (
    TestingSessionLocal,
    _override_get_db,
)

_PATCHES = (
    patch("app.services.token_blacklist.token_blacklist.is_blacklisted", return_value=False),
    patch("app.services.token_blacklist.token_blacklist.blacklist_token"),
    patch("app.core.rate_limit_middleware.RateLimitMiddleware.dispatch", side_effect=None),
    patch("workers.common.queue.QueueManager.enqueue", return_value=None),
    patch("app.services.websocket.manager.manager.start_subscriber", return_value=None),
)


def _get_test_app():
    """Return the FastAPI app with test DB + mocked externals."""
    from app.db.session import get_db

    app.dependency_overrides[get_db] = _override_get_db
    return app


def _register_and_login_sync(client: TestClient, email: str, name: str, password: str) -> str:
    """Register + login synchronously via TestClient, return JWT access token."""
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "name": name})
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _create_session_sync(client: TestClient, token: str) -> str:
    """Create a streaming session, return its UUID string."""
    resp = client.post(
        "/api/v1/sessions/",
        json={"youtube_video_id": f"ws_test_{uuid.uuid4().hex[:8]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp.json()["id"]


async def _passthrough_dispatch(request, call_next):
    """Bypass rate limiting in tests."""
    return await call_next(request)


def test_websocket_rejects_connection_without_token():
    """Connect then send non-auth message → server closes with code 4001."""
    test_app = _get_test_app()
    session_id = str(uuid.uuid4())

    with (
        patch("app.services.token_blacklist.token_blacklist.is_blacklisted", return_value=False),
        patch("app.services.token_blacklist.token_blacklist.blacklist_token"),
        patch("app.core.rate_limit_middleware.RateLimitMiddleware.dispatch", side_effect=_passthrough_dispatch),
        patch("workers.common.queue.QueueManager.enqueue", return_value=None),
        patch("app.services.websocket.manager.manager.start_subscriber", return_value=None),
    ):
        with TestClient(test_app) as tc:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with tc.websocket_connect(f"/ws/{session_id}") as ws:
                    # Send a message that is valid JSON but not an auth message
                    ws.send_json({"type": "not_auth"})
                    ws.receive_json()  # triggers the disconnect exception

            assert exc_info.value.code == 4001

    app.dependency_overrides.clear()


def test_websocket_rejects_invalid_token():
    """Connect with token='garbage' in auth message → close code 4001."""
    test_app = _get_test_app()
    session_id = str(uuid.uuid4())

    with (
        patch("app.services.token_blacklist.token_blacklist.is_blacklisted", return_value=False),
        patch("app.services.token_blacklist.token_blacklist.blacklist_token"),
        patch("app.core.rate_limit_middleware.RateLimitMiddleware.dispatch", side_effect=_passthrough_dispatch),
        patch("workers.common.queue.QueueManager.enqueue", return_value=None),
        patch("app.services.websocket.manager.manager.start_subscriber", return_value=None),
    ):
        with TestClient(test_app) as tc:
            with pytest.raises(WebSocketDisconnect) as exc_info:
                with tc.websocket_connect(f"/ws/{session_id}") as ws:
                    ws.send_json({"type": "auth", "token": "garbage"})
                    ws.receive_json()

            assert exc_info.value.code == 4001

    app.dependency_overrides.clear()


def test_websocket_accepts_valid_owner_connection():
    """Register → login → create session → WS connect with valid token → connection accepted."""
    test_app = _get_test_app()

    with (
        patch("app.services.token_blacklist.token_blacklist.is_blacklisted", return_value=False),
        patch("app.services.token_blacklist.token_blacklist.blacklist_token"),
        patch("app.core.rate_limit_middleware.RateLimitMiddleware.dispatch", side_effect=_passthrough_dispatch),
        patch("workers.common.queue.QueueManager.enqueue", return_value=None),
        patch("app.services.websocket.manager.manager.start_subscriber", return_value=None),
        patch("app.api.v1.websocket.SessionLocal", TestingSessionLocal),
    ):
        with TestClient(test_app) as tc:
            token = _register_and_login_sync(tc, "ws_owner@test.com", "WS Owner", "password123")
            session_id = _create_session_sync(tc, token)

            with tc.websocket_connect(f"/ws/{session_id}") as ws:
                ws.send_json({"type": "auth", "token": token})
                msg = ws.receive_json()
                assert msg["type"] == "connected"

    app.dependency_overrides.clear()


def test_websocket_rejects_wrong_teacher_session():
    """Teacher A creates session → Teacher B connects with own token → close code 4003."""
    test_app = _get_test_app()

    with (
        patch("app.services.token_blacklist.token_blacklist.is_blacklisted", return_value=False),
        patch("app.services.token_blacklist.token_blacklist.blacklist_token"),
        patch("app.core.rate_limit_middleware.RateLimitMiddleware.dispatch", side_effect=_passthrough_dispatch),
        patch("workers.common.queue.QueueManager.enqueue", return_value=None),
        patch("app.services.websocket.manager.manager.start_subscriber", return_value=None),
        patch("app.api.v1.websocket.SessionLocal", TestingSessionLocal),
    ):
        with TestClient(test_app) as tc:
            token_a = _register_and_login_sync(tc, "ws_a@test.com", "Teacher A", "password123")
            token_b = _register_and_login_sync(tc, "ws_b@test.com", "Teacher B", "password456")
            session_id = _create_session_sync(tc, token_a)

            with pytest.raises(WebSocketDisconnect) as exc_info:
                with tc.websocket_connect(f"/ws/{session_id}") as ws:
                    ws.send_json({"type": "auth", "token": token_b})
                    ws.receive_json()

            assert exc_info.value.code == 4003

    app.dependency_overrides.clear()
