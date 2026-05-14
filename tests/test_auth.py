"""Authentication & authorization tests."""
from __future__ import annotations


def test_register_and_login_succeeds(client):
    payload = {
        "username": "alice",
        "email": "alice@library.example.com",
        "full_name": "Alice",
        "password": "Strong@Pass1",
    }
    r = client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alice"
    assert body["role"] == "member"
    assert "id" in body and body["is_active"] is True

    r = client.post(
        "/api/v1/auth/login",
        data={"username": "alice", "password": "Strong@Pass1"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert isinstance(token, str) and len(token) > 20


def test_register_duplicate_username_conflicts(client):
    payload = {
        "username": "bob",
        "email": "bob@library.example.com",
        "password": "Strong@Pass1",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    dup = client.post("/api/v1/auth/register", json=payload)
    assert dup.status_code == 409
    assert "already" in dup.json()["detail"].lower()


def test_register_validation_error(client):
    bad = {"username": "x", "email": "not-an-email", "password": "short"}
    r = client.post("/api/v1/auth/register", json=bad)
    assert r.status_code == 422


def test_login_with_wrong_password(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "carol",
            "email": "carol@library.example.com",
            "password": "Strong@Pass1",
        },
    )
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "carol", "password": "WrongPass1"},
    )
    assert r.status_code == 401


def test_protected_endpoint_requires_token(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_returns_current_user(client, member_token, auth_headers):
    r = client.get("/api/v1/auth/me", headers=auth_headers(member_token))
    assert r.status_code == 200
    assert r.json()["role"] == "member"


def test_admin_seeded_and_can_login(client, admin_token):
    assert isinstance(admin_token, str) and admin_token


def test_invalid_token_rejected(client, auth_headers):
    r = client.get("/api/v1/auth/me", headers=auth_headers("not.a.real.token"))
    assert r.status_code == 401
