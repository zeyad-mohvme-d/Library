"""FastAPI dependencies: DB session, current user, role guards."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.security import JWTError, decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

# tokenUrl points at our JSON login endpoint so Swagger's "Authorize" works.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the current user from the JWT in ``Authorization: Bearer <token>``."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exc

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exc
        user_id = int(sub)
    except (JWTError, ValueError) as exc:
        logger.info("JWT validation failed: {}", exc)
        raise credentials_exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        logger.info("Token user_id={} not found or inactive", user_id)
        raise credentials_exc
    return user


def require_admin(current: User = Depends(get_current_user)) -> User:
    """403 unless current user is an Admin/Librarian."""
    if current.role != UserRole.ADMIN:
        logger.info("Forbidden: user {} attempted admin-only action", current.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current


def require_member(current: User = Depends(get_current_user)) -> User:
    """403 unless current user is a Member."""
    if current.role != UserRole.MEMBER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Member privileges required",
        )
    return current
