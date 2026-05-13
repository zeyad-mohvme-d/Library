"""Pydantic schemas for User and authentication."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


# ---------- Base / shared ---------- #
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.\-]+$")
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)


# ---------- Auth I/O ---------- #
class UserRegister(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")
    user: "UserOut"


# ---------- User read ---------- #
class UserOut(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Resolve forward ref
TokenResponse.model_rebuild()
