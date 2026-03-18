"""Black-box contract tests for dashboard endpoints."""

import uuid

from httpx import AsyncClient
from sqlalchemy.orm import sessionmaker
from tests.conftest import engine

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_cluster_and_answer(session_id: str) -> tuple[str, str]:
    """Insert a cluster + answer directly via SQLAlchemy, return (answer_id, cluster_id)."""
    from app.db.models.answer import Answer
    from app.db.models.cluster import Cluster

    db = TestingSessionLocal()
    try:
        cluster = Cluster(
            session_id=session_id,
            title="Test Cluster",
            similarity_threshold=0.8,
        )
        db.add(cluster)
        db.flush()

        answer = Answer(
            cluster_id=cluster.id,
            text="Original answer text",
        )
        db.add(answer)
        db.commit()
        return str(answer.id), str(cluster.id)
    finally:
        db.close()


async def test_manual_question_creates_comments(client: AsyncClient, auth_headers: dict, session_id: str):
    resp = await client.post(
        f"/api/v1/dashboard/sessions/{session_id}/manual-question",
        json={"text": "Q1\nQ2\nQ3"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json() == {"created": 3}


async def test_manual_question_max_10(client: AsyncClient, auth_headers: dict, session_id: str):
    questions = "\n".join(f"Question {i}" for i in range(15))
    resp = await client.post(
        f"/api/v1/dashboard/sessions/{session_id}/manual-question",
        json={"text": questions},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json() == {"created": 10}


async def test_manual_question_nonexistent_session(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/dashboard/sessions/{fake_id}/manual-question",
        json={"text": "Some question"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_session_stats_empty(client: AsyncClient, auth_headers: dict, session_id: str):
    resp = await client.get(
        f"/api/v1/dashboard/sessions/{session_id}/stats",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_comments"] == 0
    assert body["questions"] == 0
    assert body["answered"] == 0
    assert body["clusters"] == 0
    assert body["answers_generated"] == 0
    assert body["answers_posted"] == 0


async def test_edit_answer(client: AsyncClient, auth_headers: dict, session_id: str):
    answer_id, _ = _create_cluster_and_answer(session_id)
    resp = await client.patch(
        f"/api/v1/dashboard/answers/{answer_id}",
        json={"text": "Edited answer text"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["text"] == "Edited answer text"
    assert "id" in body
    assert "cluster_id" in body
    assert "created_at" in body


async def test_edit_answer_not_found(client: AsyncClient, auth_headers: dict):
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/dashboard/answers/{fake_id}",
        json={"text": "Doesn't matter"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_approve_answer(client: AsyncClient, auth_headers: dict, session_id: str):
    answer_id, _ = _create_cluster_and_answer(session_id)
    resp = await client.post(
        f"/api/v1/dashboard/answers/{answer_id}/approve",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == answer_id
    assert "text" in body
    assert "cluster_id" in body
