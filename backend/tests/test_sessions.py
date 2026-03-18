"""Black-box contract tests for session endpoints."""

import uuid

from httpx import AsyncClient


async def test_create_session(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/sessions/",
        json={"youtube_video_id": "vid_create_test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["youtube_video_id"] == "vid_create_test"
    assert body["is_active"] is True
    assert "teacher_id" in body


async def test_list_sessions_empty(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/sessions/", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_sessions_returns_own(client: AsyncClient, auth_headers: dict, session_id: str):
    resp = await client.get("/api/v1/sessions/", headers=auth_headers)
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 1
    ids = [s["id"] for s in sessions]
    assert session_id in ids


async def test_get_session_by_id(client: AsyncClient, auth_headers: dict, session_id: str):
    resp = await client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == session_id
    assert body["is_active"] is True


async def test_update_session(client: AsyncClient, auth_headers: dict, session_id: str):
    resp = await client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"title": "Updated Title"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


async def test_end_session(client: AsyncClient, auth_headers: dict, session_id: str):
    resp = await client.post(
        f"/api/v1/sessions/{session_id}/end",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_active"] is False
    assert body["ended_at"] is not None


async def test_get_nonexistent_session(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/sessions/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404
