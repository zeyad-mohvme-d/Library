"""Pydantic schemas for borrow / return operations."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.borrow_record import BorrowStatus


class BorrowCreate(BaseModel):
    book_id: int = Field(..., gt=0)
    days: int | None = Field(
        default=None,
        ge=1,
        le=90,
        description="Borrow duration in days (defaults to library policy).",
    )


class BorrowRecordOut(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrowed_at: datetime
    due_at: datetime
    returned_at: datetime | None
    status: BorrowStatus

    # Friendly nested info
    book_title: str | None = None
    book_author: str | None = None
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)


class BorrowHistoryOut(BaseModel):
    total: int
    items: list[BorrowRecordOut]
