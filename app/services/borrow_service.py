"""Borrow / return service with full business-rule validation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.exceptions import BusinessRuleError, ForbiddenError, NotFoundError
from app.core.logging import logger
from app.core.metrics import borrow_counter, return_counter
from app.models.book import Book
from app.models.borrow_record import BorrowRecord, BorrowStatus
from app.models.user import User, UserRole
from app.services.book_service import invalidate_cache as invalidate_books_cache


# ---- helpers ----------------------------------------------------------- #
def _active_borrow_count(db: Session, user_id: int) -> int:
    return db.execute(
        select(func.count())
        .select_from(BorrowRecord)
        .where(
            BorrowRecord.user_id == user_id,
            BorrowRecord.status == BorrowStatus.BORROWED,
        )
    ).scalar_one()


def _has_active_borrow(db: Session, user_id: int, book_id: int) -> bool:
    return (
        db.execute(
            select(BorrowRecord).where(
                BorrowRecord.user_id == user_id,
                BorrowRecord.book_id == book_id,
                BorrowRecord.status == BorrowStatus.BORROWED,
            )
        ).scalar_one_or_none()
        is not None
    )


def _augment(record: BorrowRecord) -> dict:
    return {
        "id": record.id,
        "user_id": record.user_id,
        "book_id": record.book_id,
        "borrowed_at": record.borrowed_at,
        "due_at": record.due_at,
        "returned_at": record.returned_at,
        "status": record.status,
        "book_title": record.book.title if record.book else None,
        "book_author": record.book.author if record.book else None,
        "username": record.user.username if record.user else None,
    }


# ---- mutations --------------------------------------------------------- #
def borrow_book(
    db: Session, user: User, book_id: int, days: int | None = None
) -> BorrowRecord:
    """Borrow a book for ``user``.

    Enforces:
        * Book exists and has available copies
        * User has not already borrowed this book (and not yet returned it)
        * User has not exceeded ``MAX_BORROW_PER_USER``
    """
    book = db.get(Book, book_id)
    if book is None:
        borrow_counter.labels(status="denied").inc()
        raise NotFoundError(f"Book id={book_id} not found")

    if book.available_copies <= 0:
        borrow_counter.labels(status="denied").inc()
        logger.info(
            "Borrow denied: book id={} unavailable for user={}", book.id, user.id
        )
        raise BusinessRuleError("This book is currently unavailable")

    if _has_active_borrow(db, user.id, book.id):
        borrow_counter.labels(status="denied").inc()
        raise BusinessRuleError("You already have an active borrow for this book")

    active = _active_borrow_count(db, user.id)
    if active >= settings.max_borrow_per_user:
        borrow_counter.labels(status="denied").inc()
        logger.info(
            "Borrow denied: user={} hit limit ({}/{})",
            user.id,
            active,
            settings.max_borrow_per_user,
        )
        raise BusinessRuleError(
            f"Borrow limit reached ({settings.max_borrow_per_user} active loans)"
        )

    duration_days = days or settings.default_borrow_days
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    record = BorrowRecord(
        user_id=user.id,
        book_id=book.id,
        borrowed_at=now,
        due_at=now + timedelta(days=duration_days),
        status=BorrowStatus.BORROWED,
    )

    book.available_copies -= 1

    db.add(record)
    db.commit()
    db.refresh(record)
    # Force-load relationships for the response.
    db.refresh(record, attribute_names=["book", "user"])

    invalidate_books_cache()
    borrow_counter.labels(status="success").inc()
    logger.info("BORROW user={} book={} record={}", user.id, book.id, record.id)
    return record


def return_book(db: Session, user: User, record_id: int) -> BorrowRecord:
    """Return a borrowed book.

    Members can only return their own active loans; admins can return on
    behalf of any member.
    """
    record = db.get(BorrowRecord, record_id)
    if record is None:
        raise NotFoundError(f"Borrow record id={record_id} not found")

    if user.role != UserRole.ADMIN and record.user_id != user.id:
        raise ForbiddenError("You cannot return another user's borrow record")

    if record.status == BorrowStatus.RETURNED:
        raise BusinessRuleError("This borrow has already been returned")

    record.status = BorrowStatus.RETURNED
    record.returned_at = datetime.now(timezone.utc).replace(tzinfo=None)

    book = db.get(Book, record.book_id)
    if book is not None and book.available_copies < book.total_copies:
        book.available_copies += 1

    db.commit()
    db.refresh(record)
    db.refresh(record, attribute_names=["book", "user"])

    invalidate_books_cache()
    return_counter.inc()
    logger.info("RETURN user={} record={}", user.id, record.id)
    return record


# ---- queries ----------------------------------------------------------- #
def list_my_history(db: Session, user: User, skip: int = 0, limit: int = 50) -> dict:
    stmt = (
        select(BorrowRecord)
        .options(joinedload(BorrowRecord.book), joinedload(BorrowRecord.user))
        .where(BorrowRecord.user_id == user.id)
        .order_by(BorrowRecord.borrowed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = db.execute(stmt).scalars().all()
    total = db.execute(
        select(func.count()).select_from(BorrowRecord).where(BorrowRecord.user_id == user.id)
    ).scalar_one()
    return {"total": total, "items": [_augment(r) for r in items]}


def list_all_history(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    user_id: int | None = None,
    book_id: int | None = None,
    status_filter: BorrowStatus | None = None,
) -> dict:
    stmt = (
        select(BorrowRecord)
        .options(joinedload(BorrowRecord.book), joinedload(BorrowRecord.user))
        .order_by(BorrowRecord.borrowed_at.desc())
    )
    count_stmt = select(func.count()).select_from(BorrowRecord)
    if user_id is not None:
        stmt = stmt.where(BorrowRecord.user_id == user_id)
        count_stmt = count_stmt.where(BorrowRecord.user_id == user_id)
    if book_id is not None:
        stmt = stmt.where(BorrowRecord.book_id == book_id)
        count_stmt = count_stmt.where(BorrowRecord.book_id == book_id)
    if status_filter is not None:
        stmt = stmt.where(BorrowRecord.status == status_filter)
        count_stmt = count_stmt.where(BorrowRecord.status == status_filter)

    stmt = stmt.offset(skip).limit(limit)
    items = db.execute(stmt).scalars().all()
    total = db.execute(count_stmt).scalar_one()
    return {"total": total, "items": [_augment(r) for r in items]}
