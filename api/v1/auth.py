"""Authentication routes: register & login."""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserOut, UserRegister
from app.services import user_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new member account",
)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> User:
    return user_service.register_user(db, payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with username/email + password — returns a JWT",
)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """OAuth2 password flow — accepts ``username`` (or email) + ``password``."""
    from app.schemas.user import UserLogin  # local import to avoid cycle

    payload = UserLogin(username=form.username, password=form.password)
    user, token, expires_in = user_service.authenticate(db, payload)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": UserOut.model_validate(user),
    }


@router.get("/me", response_model=UserOut, summary="Return the current user")
def me(current: User = Depends(get_current_user)) -> User:
    return current
