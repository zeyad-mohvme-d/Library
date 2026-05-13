"""Books CRUD routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.book import BookCreate, BookListOut, BookOut, BookUpdate
from app.services import book_service

router = APIRouter(prefix="/books", tags=["Books"])


@router.get(
    "",
    response_model=BookListOut,
    summary="List books (cached, public)",
)
def list_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, description="Search title or author"),
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Listing books does NOT require authentication (catalog browsing)."""
    return book_service.list_books(db, skip=skip, limit=limit, q=q, category=category)


@router.get(
    "/{book_id}",
    response_model=BookOut,
    summary="Get a single book by id (cached, public)",
)
def get_book(book_id: int, db: Session = Depends(get_db)):
    return book_service.get_book(db, book_id)


@router.post(
    "",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new book — admin only",
)
def create_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return book_service.create_book(db, payload)


@router.put(
    "/{book_id}",
    response_model=BookOut,
    summary="Update a book — admin only",
)
def update_book(
    book_id: int,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return book_service.update_book(db, book_id, payload)


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book — admin only",
)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    book_service.delete_book(db, book_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
