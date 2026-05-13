"""BorrowRecord ORM model."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class BorrowStatus(str, enum.Enum):
    BORROWED = "borrowed"
    RETURNED = "returned"


class BorrowRecord(Base):
    __tablename__ = "borrow_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )

    borrowed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[BorrowStatus] = mapped_column(
        Enum(BorrowStatus, name="borrow_status"),
        nullable=False,
        default=BorrowStatus.BORROWED,
        index=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="borrow_records")
    book: Mapped["Book"] = relationship("Book", back_populates="borrow_records")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<BorrowRecord id={self.id} user={self.user_id} "
            f"book={self.book_id} status={self.status.value}>"
        )
