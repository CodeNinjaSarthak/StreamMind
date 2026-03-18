"""Black-box contract tests for auth endpoints."""

import pytest
from httpx import AsyncClient


@pytest.fixture()
def _teacher_data():
    return {"email": "auth_test@test.com", "password": "password123", "name": "Auth Tester"}


async def test_register_success(client: AsyncClient, _teacher_data: dict):
    resp = await client.post("/api/v1/auth/register", json=_teacher_data)
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["email"] == _teacher_data["email"]
    assert body["name"] == _teacher_data["name"]
    assert body["is_active"] is True


async def test_register_duplicate_email(client: AsyncClient, _teacher_data: dict):
    await client.post("/api/v1/auth/register", json=_teacher_data)
    resp = await client.post("/api/v1/auth/register", json=_teacher_data)
    assert resp.status_code == 400


async def test_login_success(client: AsyncClient, _teacher_data: dict):
    await client.post("/api/v1/auth/register", json=_teacher_data)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _teacher_data["email"], "password": _teacher_data["password"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert "expires_in" in body


async def test_login_wrong_password(client: AsyncClient, _teacher_data: dict):
    await client.post("/api/v1/auth/register", json=_teacher_data)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _teacher_data["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_email(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "password123"},
    )
    assert resp.status_code == 401


async def test_me_with_valid_token(client: AsyncClient, _teacher_data: dict):
    await client.post("/api/v1/auth/register", json=_teacher_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _teacher_data["email"], "password": _teacher_data["password"]},
    )
    token = login_resp.json()["access_token"]

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == _teacher_data["email"]
    assert body["name"] == _teacher_data["name"]


async def test_me_without_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in [401, 403]


async def test_refresh_token(client: AsyncClient, _teacher_data: dict):
    await client.post("/api/v1/auth/register", json=_teacher_data)
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _teacher_data["email"], "password": _teacher_data["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
