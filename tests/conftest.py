"""Pytest fixtures: per-session SQLite DB + TestClient with seeded admin."""
from __future__ import annotations

import os
import uuid

# Use an in-memory shared SQLite DB. The `cache=shared` URI lets multiple
# connections see the same in-memory database, which TestClient needs.
_DB_NAME = f"library_test_{uuid.uuid4().hex[:12]}"
os.environ["DATABASE_URL"] = (
    f"sqlite+pysqlite:///file:{_DB_NAME}?mode=memory&cache=shared&uri=true"
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-tests-only-do-not-use-in-prod"
os.environ["DEFAULT_ADMIN_USERNAME"] = "admin"
os.environ["DEFAULT_ADMIN_PASSWORD"] = "Admin@12345"
os.environ["DEFAULT_ADMIN_EMAIL"] = "admin@library.example.com"
os.environ["MAX_BORROW_PER_USER"] = "3"
os.environ["CACHE_TTL_SECONDS"] = "60"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6390/15"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.core.config as _config  # noqa: E402
_config.settings.database_url = os.environ["DATABASE_URL"]
_config.settings.jwt_secret_key = os.environ["JWT_SECRET_KEY"]
_config.settings.max_borrow_per_user = int(os.environ["MAX_BORROW_PER_USER"])
_config.settings.redis_url = os.environ["REDIS_URL"]

import app.db.session as db_session  # noqa: E402
from app.db.session import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    test_engine = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"check_same_thread": False, "uri": True},
        poolclass=StaticPool,
        future=True,
    )
    test_session = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    db_session.engine = test_engine
    db_session.SessionLocal = test_session

    from app.models import Book, BorrowRecord, User  # noqa: F401

    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client(_setup_database):
    from app.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client) -> str:
    res = client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "Admin@12345"},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


@pytest.fixture()
def member_token(client) -> str:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "username": f"member_{suffix}",
        "email": f"member_{suffix}@library.example.com",
        "full_name": "Test Member",
        "password": "Member@12345",
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text

    login = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


@pytest.fixture()
def auth_headers():
    def _make(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    return _make
