"""Black-box ownership boundary tests: teacher A cannot access teacher B's resources."""

from httpx import AsyncClient


async def _create_session(client: AsyncClient, auth_headers: dict) -> str:
    """Create a session via API, return its UUID string."""
    resp = await client.post(
        "/api/v1/sessions/",
        json={"youtube_video_id": "vid_security_test"},
        headers=auth_headers,
    )
    return resp.json()["id"]


async def test_teacher_b_cannot_get_teacher_a_session(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    session_id = await _create_session(client, auth_headers)
    resp = await client.get(
        f"/api/v1/sessions/{session_id}",
        headers=second_auth_headers,
    )
    assert resp.status_code in [403, 404]


async def test_teacher_b_cannot_update_teacher_a_session(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    session_id = await _create_session(client, auth_headers)
    resp = await client.patch(
        f"/api/v1/sessions/{session_id}",
        json={"title": "Hijacked"},
        headers=second_auth_headers,
    )
    assert resp.status_code in [403, 404]


async def test_teacher_b_cannot_end_teacher_a_session(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    session_id = await _create_session(client, auth_headers)
    resp = await client.post(
        f"/api/v1/sessions/{session_id}/end",
        headers=second_auth_headers,
    )
    assert resp.status_code in [403, 404]


async def test_teacher_b_cannot_see_teacher_a_sessions_in_list(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    a_session_id = await _create_session(client, auth_headers)
    b_session_id = await _create_session(client, second_auth_headers)

    resp = await client.get("/api/v1/sessions/", headers=second_auth_headers)
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert b_session_id in ids
    assert a_session_id not in ids


async def test_teacher_b_cannot_submit_manual_question_to_teacher_a_session(
    client: AsyncClient, auth_headers: dict, second_auth_headers: dict
):
    session_id = await _create_session(client, auth_headers)
    resp = await client.post(
        f"/api/v1/dashboard/sessions/{session_id}/manual-question",
        json={"text": "Unauthorized question"},
        headers=second_auth_headers,
    )
    assert resp.status_code in [403, 404]
