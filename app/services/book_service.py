"""Book service — CRUD with cache-aside + invalidation."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import logger
from app.core.metrics import cache_hits
from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate

# ---- cache helpers ----------------------------------------------------- #
BOOKS_NAMESPACE = "books"


def _list_key(skip: int, limit: int, q: str | None, category: str | None) -> str:
    return f"{BOOKS_NAMESPACE}:list:skip={skip}:limit={limit}:q={q or ''}:cat={category or ''}"


def _detail_key(book_id: int) -> str:
    return f"{BOOKS_NAMESPACE}:detail:{book_id}"


def invalidate_cache() -> None:
    """Wipe every books:* key — called after any mutation."""
    n = cache.delete_pattern(f"{BOOKS_NAMESPACE}:*")
    cache_hits.labels(event="invalidate").inc(n or 1)


# ---- queries ----------------------------------------------------------- #
def _serialize(book: Book) -> dict:
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "description": book.description,
        "category": book.category,
        "total_copies": book.total_copies,
        "available_copies": book.available_copies,
        "created_at": book.created_at.isoformat() if book.created_at else None,
        "updated_at": book.updated_at.isoformat() if book.updated_at else None,
    }


def list_books(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    q: str | None = None,
    category: str | None = None,
) -> dict:
    """Cache-aside list with optional search & category filter."""
    key = _list_key(skip, limit, q, category)

    cached = cache.get(key)
    if cached is not None:
        cache_hits.labels(event="hit").inc()
        return cached
    cache_hits.labels(event="miss").inc()

    stmt = select(Book)
    count_stmt = select(func.count()).select_from(Book)
    if q:
        like = f"%{q}%"
        cond = or_(Book.title.ilike(like), Book.author.ilike(like))
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if category:
        stmt = stmt.where(Book.category == category)
        count_stmt = count_stmt.where(Book.category == category)

    stmt = stmt.order_by(Book.id.desc()).offset(skip).limit(limit)
    items = db.execute(stmt).scalars().all()
    total = db.execute(count_stmt).scalar_one()

    payload = {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [_serialize(b) for b in items],
    }
    cache.set(key, payload)
    return payload


def get_book(db: Session, book_id: int) -> dict:
    key = _detail_key(book_id)
    cached = cache.get(key)
    if cached is not None:
        cache_hits.labels(event="hit").inc()
        return cached
    cache_hits.labels(event="miss").inc()

    book = db.get(Book, book_id)
    if book is None:
        raise NotFoundError(f"Book id={book_id} not found")

    payload = _serialize(book)
    cache.set(key, payload)
    return payload


def get_book_orm(db: Session, book_id: int) -> Book:
    book = db.get(Book, book_id)
    if book is None:
        raise NotFoundError(f"Book id={book_id} not found")
    return book


# ---- mutations --------------------------------------------------------- #
def create_book(db: Session, payload: BookCreate) -> Book:
    if payload.isbn:
        existing = db.execute(
            select(Book).where(Book.isbn == payload.isbn)
        ).scalar_one_or_none()
        if existing is not None:
            raise ConflictError(f"A book with ISBN {payload.isbn} already exists")

    available = (
        payload.available_copies
        if payload.available_copies is not None
        else payload.total_copies
    )
    if available > payload.total_copies:
        raise ConflictError("available_copies cannot exceed total_copies")

    book = Book(
        title=payload.title,
        author=payload.author,
        isbn=payload.isbn,
        description=payload.description,
        category=payload.category,
        total_copies=payload.total_copies,
        available_copies=available,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    invalidate_cache()
    logger.info("Book created id={} title={!r}", book.id, book.title)
    return book


def update_book(db: Session, book_id: int, payload: BookUpdate) -> Book:
    book = get_book_orm(db, book_id)

    data = payload.model_dump(exclude_unset=True)

    # Validate the available/total relationship across the change.
    new_total = data.get("total_copies", book.total_copies)
    new_avail = data.get("available_copies", book.available_copies)

    # If only total changed, keep delta on availability sensible.
    if "total_copies" in data and "available_copies" not in data:
        delta = new_total - book.total_copies
        new_avail = max(0, book.available_copies + delta)

    if new_avail > new_total:
        raise ConflictError("available_copies cannot exceed total_copies")

    if "isbn" in data and data["isbn"] is not None:
        clash = db.execute(
            select(Book).where(Book.isbn == data["isbn"], Book.id != book_id)
        ).scalar_one_or_none()
        if clash is not None:
            raise ConflictError(f"ISBN {data['isbn']} already used by another book")

    for field, value in data.items():
        setattr(book, field, value)
    book.total_copies = new_total
    book.available_copies = new_avail

    db.commit()
    db.refresh(book)

    invalidate_cache()
    logger.info("Book updated id={}", book.id)
    return book


def delete_book(db: Session, book_id: int) -> None:
    book = get_book_orm(db, book_id)
    db.delete(book)
    db.commit()

    invalidate_cache()
    logger.info("Book deleted id={}", book_id)
