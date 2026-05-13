"""SQLAlchemy engine, session factory, and base model."""
from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


def _make_engine(url: str):
    """Create an engine, picking the right kwargs for the dialect."""
    kwargs: dict = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # check_same_thread for SQLite + multi-threaded TestClient.
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(pool_recycle=1800, pool_size=10, max_overflow=20)
    return create_engine(url, **kwargs)


engine = _make_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
