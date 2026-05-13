"""Pydantic schemas for Book CRUD."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=32)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    total_copies: int = Field(default=1, ge=0)


class BookCreate(BookBase):
    available_copies: int | None = Field(
        default=None,
        ge=0,
        description="Defaults to ``total_copies`` if omitted.",
    )

    @field_validator("isbn")
    @classmethod
    def _normalize_isbn(cls, v: str | None) -> str | None:
        if v is None:
            return v
        cleaned = v.replace("-", "").replace(" ", "").strip()
        return cleaned or None


class BookUpdate(BaseModel):
    """All fields optional — partial update."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=32)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    total_copies: int | None = Field(default=None, ge=0)
    available_copies: int | None = Field(default=None, ge=0)


class BookOut(BookBase):
    id: int
    available_copies: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookListOut(BaseModel):
    """Paginated list response."""

    total: int
    skip: int
    limit: int
    items: list[BookOut]
