"""Borrow / return routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.borrow_record import BorrowStatus
from app.models.user import User
from app.schemas.borrow import BorrowCreate, BorrowHistoryOut, BorrowRecordOut
from app.services import borrow_service

router = APIRouter(prefix="/borrow", tags=["Borrow"])


@router.post(
    "",
    response_model=BorrowRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Borrow a book (members & admins)",
)
def borrow(
    payload: BorrowCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    record = borrow_service.borrow_book(db, current, payload.book_id, payload.days)
    return BorrowRecordOut(
        id=record.id,
        user_id=record.user_id,
        book_id=record.book_id,
        borrowed_at=record.borrowed_at,
        due_at=record.due_at,
        returned_at=record.returned_at,
        status=record.status,
        book_title=record.book.title if record.book else None,
        book_author=record.book.author if record.book else None,
        username=record.user.username if record.user else None,
    )


@router.post(
    "/{record_id}/return",
    response_model=BorrowRecordOut,
    summary="Return a previously borrowed book",
)
def return_(
    record_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    record = borrow_service.return_book(db, current, record_id)
    return BorrowRecordOut(
        id=record.id,
        user_id=record.user_id,
        book_id=record.book_id,
        borrowed_at=record.borrowed_at,
        due_at=record.due_at,
        returned_at=record.returned_at,
        status=record.status,
        book_title=record.book.title if record.book else None,
        book_author=record.book.author if record.book else None,
        username=record.user.username if record.user else None,
    )


@router.get(
    "/me",
    response_model=BorrowHistoryOut,
    summary="My borrow history",
)
def my_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return borrow_service.list_my_history(db, current, skip=skip, limit=limit)


@router.get(
    "",
    response_model=BorrowHistoryOut,
    summary="All borrow records — admin only",
)
def all_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user_id: int | None = Query(None),
    book_id: int | None = Query(None),
    status_filter: BorrowStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return borrow_service.list_all_history(
        db,
        skip=skip,
        limit=limit,
        user_id=user_id,
        book_id=book_id,
        status_filter=status_filter,
    )
