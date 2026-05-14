"""Books CRUD + role-based access tests."""
from __future__ import annotations

import uuid


def _book_payload(**overrides):
    base = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": f"978-{uuid.uuid4().int % 10**10:010d}",
        "description": "A handbook of agile software craftsmanship.",
        "category": "Software",
        "total_copies": 3,
    }
    base.update(overrides)
    return base


def test_list_books_public(client):
    r = client.get("/api/v1/books")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and "total" in body


def test_member_cannot_create_book(client, member_token, auth_headers):
    r = client.post(
        "/api/v1/books", json=_book_payload(), headers=auth_headers(member_token)
    )
    assert r.status_code == 403


def test_admin_can_create_book(client, admin_token, auth_headers):
    r = client.post(
        "/api/v1/books", json=_book_payload(), headers=auth_headers(admin_token)
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Clean Code"
    assert body["available_copies"] == body["total_copies"] == 3


def test_get_book_by_id(client, admin_token, auth_headers):
    created = client.post(
        "/api/v1/books",
        json=_book_payload(title="Refactoring"),
        headers=auth_headers(admin_token),
    ).json()
    r = client.get(f"/api/v1/books/{created['id']}")
    assert r.status_code == 200
    assert r.json()["title"] == "Refactoring"


def test_get_missing_book_returns_404(client):
    r = client.get("/api/v1/books/999999")
    assert r.status_code == 404


def test_update_book_admin_only(client, admin_token, member_token, auth_headers):
    created = client.post(
        "/api/v1/books", json=_book_payload(), headers=auth_headers(admin_token)
    ).json()

    r_member = client.put(
        f"/api/v1/books/{created['id']}",
        json={"title": "Hacked"},
        headers=auth_headers(member_token),
    )
    assert r_member.status_code == 403

    r_admin = client.put(
        f"/api/v1/books/{created['id']}",
        json={"title": "Clean Code (2nd ed.)"},
        headers=auth_headers(admin_token),
    )
    assert r_admin.status_code == 200
    assert r_admin.json()["title"] == "Clean Code (2nd ed.)"


def test_delete_book_admin_only(client, admin_token, member_token, auth_headers):
    created = client.post(
        "/api/v1/books", json=_book_payload(), headers=auth_headers(admin_token)
    ).json()

    r_member = client.delete(
        f"/api/v1/books/{created['id']}", headers=auth_headers(member_token)
    )
    assert r_member.status_code == 403

    r_admin = client.delete(
        f"/api/v1/books/{created['id']}", headers=auth_headers(admin_token)
    )
    assert r_admin.status_code == 204
    assert client.get(f"/api/v1/books/{created['id']}").status_code == 404


def test_create_book_with_duplicate_isbn_conflicts(client, admin_token, auth_headers):
    payload = _book_payload(isbn="978-0000000001")
    assert (
        client.post("/api/v1/books", json=payload, headers=auth_headers(admin_token)).status_code
        == 201
    )
    dup = client.post("/api/v1/books", json=payload, headers=auth_headers(admin_token))
    assert dup.status_code == 409


def test_search_books(client, admin_token, auth_headers):
    client.post(
        "/api/v1/books",
        json=_book_payload(title="Domain-Driven Design", author="Eric Evans"),
        headers=auth_headers(admin_token),
    )
    r = client.get("/api/v1/books?q=Evans")
    assert r.status_code == 200
    titles = [b["title"] for b in r.json()["items"]]
    assert any("Domain" in t for t in titles)
