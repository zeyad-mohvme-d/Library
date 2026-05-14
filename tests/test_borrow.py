"""Borrow / return business logic tests."""
from __future__ import annotations

import uuid


def _make_book(client, admin_headers, total_copies: int = 1, **overrides):
    payload = {
        "title": overrides.get("title", "Test Book"),
        "author": "An Author",
        "isbn": f"978-{uuid.uuid4().int % 10**10:010d}",
        "total_copies": total_copies,
        **overrides,
    }
    r = client.post("/api/v1/books", json=payload, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_member_can_borrow_and_return(client, admin_token, member_token, auth_headers):
    admin_h = auth_headers(admin_token)
    member_h = auth_headers(member_token)

    book = _make_book(client, admin_h, total_copies=2)

    r = client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h)
    assert r.status_code == 201
    record = r.json()
    assert record["status"] == "borrowed"
    assert record["book_id"] == book["id"]

    # available_copies should have decremented
    assert client.get(f"/api/v1/books/{book['id']}").json()["available_copies"] == 1

    # Return
    rr = client.post(f"/api/v1/borrow/{record['id']}/return", headers=member_h)
    assert rr.status_code == 200
    assert rr.json()["status"] == "returned"
    assert client.get(f"/api/v1/books/{book['id']}").json()["available_copies"] == 2


def test_cannot_borrow_unavailable_book(client, admin_token, member_token, auth_headers):
    admin_h = auth_headers(admin_token)
    member_h = auth_headers(member_token)

    book = _make_book(client, admin_h, total_copies=1)

    r1 = client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h)
    assert r1.status_code == 201

    # Need a SECOND member to attempt the borrow (same member would hit the
    # "already borrowed" rule first).
    suffix = uuid.uuid4().hex[:8]
    other = {
        "username": f"other_{suffix}",
        "email": f"other_{suffix}@library.example.com",
        "password": "Strong@Pass1",
    }
    client.post("/api/v1/auth/register", json=other)
    other_login = client.post(
        "/api/v1/auth/login",
        data={"username": other["username"], "password": other["password"]},
    ).json()
    other_h = auth_headers(other_login["access_token"])

    r2 = client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=other_h)
    assert r2.status_code == 422
    assert "unavailable" in r2.json()["detail"].lower()


def test_cannot_double_borrow_same_book(client, admin_token, member_token, auth_headers):
    admin_h = auth_headers(admin_token)
    member_h = auth_headers(member_token)
    book = _make_book(client, admin_h, total_copies=5)

    r1 = client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h)
    assert r2.status_code == 422
    assert "already" in r2.json()["detail"].lower()


def test_borrow_limit_enforced(client, admin_token, member_token, auth_headers):
    """MAX_BORROW_PER_USER is 3 in tests/conftest.py."""
    admin_h = auth_headers(admin_token)
    member_h = auth_headers(member_token)

    for _ in range(3):
        book = _make_book(client, admin_h, total_copies=1)
        r = client.post(
            "/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h
        )
        assert r.status_code == 201

    extra = _make_book(client, admin_h, total_copies=1)
    r = client.post("/api/v1/borrow", json={"book_id": extra["id"]}, headers=member_h)
    assert r.status_code == 422
    assert "limit" in r.json()["detail"].lower()


def test_cannot_return_others_record(client, admin_token, member_token, auth_headers):
    admin_h = auth_headers(admin_token)
    member_h = auth_headers(member_token)
    book = _make_book(client, admin_h, total_copies=1)

    r = client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h)
    record_id = r.json()["id"]

    suffix = uuid.uuid4().hex[:8]
    other = {
        "username": f"other_{suffix}",
        "email": f"other_{suffix}@library.example.com",
        "password": "Strong@Pass1",
    }
    client.post("/api/v1/auth/register", json=other)
    other_login = client.post(
        "/api/v1/auth/login",
        data={"username": other["username"], "password": other["password"]},
    ).json()
    other_h = auth_headers(other_login["access_token"])

    rr = client.post(f"/api/v1/borrow/{record_id}/return", headers=other_h)
    assert rr.status_code == 403


def test_admin_can_return_on_behalf(client, admin_token, member_token, auth_headers):
    admin_h = auth_headers(admin_token)
    member_h = auth_headers(member_token)
    book = _make_book(client, admin_h, total_copies=1)

    r = client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h)
    record_id = r.json()["id"]

    rr = client.post(f"/api/v1/borrow/{record_id}/return", headers=admin_h)
    assert rr.status_code == 200


def test_my_history_only_shows_own_records(client, admin_token, member_token, auth_headers):
    admin_h = auth_headers(admin_token)
    member_h = auth_headers(member_token)
    book = _make_book(client, admin_h, total_copies=1)
    client.post("/api/v1/borrow", json={"book_id": book["id"]}, headers=member_h)

    r = client.get("/api/v1/borrow/me", headers=member_h)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert all(item["book_id"] == book["id"] for item in body["items"])


def test_admin_history_endpoint_requires_admin(client, member_token, auth_headers):
    r = client.get("/api/v1/borrow", headers=auth_headers(member_token))
    assert r.status_code == 403
