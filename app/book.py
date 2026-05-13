"""Book ORM model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.models.borrow_record import BorrowRecord


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("total_copies >= 0", name="ck_books_total_copies_non_negative"),
        CheckConstraint(
            "available_copies >= 0", name="ck_books_available_non_negative"
        ),
        CheckConstraint(
            "available_copies <= total_copies",
            name="ck_books_available_le_total",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    isbn: Mapped[str | None] = mapped_column(
        String(32), unique=True, nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    total_copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    available_copies: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    borrow_records: Mapped[List["BorrowRecord"]] = relationship(
        "BorrowRecord", back_populates="book", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Book id={self.id} title={self.title!r} avail={self.available_copies}/{self.total_copies}>"
