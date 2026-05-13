"""User-related service: registration, login, seeding the default admin."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.logging import logger
from app.core.metrics import auth_counter
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserLogin, UserRegister


def _by_username_or_email(db: Session, value: str) -> User | None:
    return db.execute(
        select(User).where((User.username == value) | (User.email == value))
    ).scalar_one_or_none()


def register_user(db: Session, payload: UserRegister) -> User:
    """Create a new Member account.

    Raises ``ConflictError`` if the username or email already exists.
    """
    existing = db.execute(
        select(User).where(
            (User.username == payload.username) | (User.email == payload.email)
        )
    ).scalar_one_or_none()
    if existing is not None:
        auth_counter.labels(event="register", result="failure").inc()
        raise ConflictError("Username or email already in use")

    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    auth_counter.labels(event="register", result="success").inc()
    logger.info("Registered new member id={} username={}", user.id, user.username)
    return user


def authenticate(db: Session, payload: UserLogin) -> tuple[User, str, int]:
    """Verify credentials, mint and return a JWT.

    Returns ``(user, access_token, expires_in_seconds)``.
    """
    user = _by_username_or_email(db, payload.username)
    if user is None or not verify_password(payload.password, user.hashed_password):
        auth_counter.labels(event="login", result="failure").inc()
        logger.warning("Login failed for username={}", payload.username)
        raise UnauthorizedError("Invalid username or password")
    if not user.is_active:
        auth_counter.labels(event="login", result="failure").inc()
        raise UnauthorizedError("Account is disabled")

    expires_in = settings.jwt_expire_minutes * 60
    token = create_access_token(subject=user.id, role=user.role.value)

    auth_counter.labels(event="login", result="success").inc()
    logger.info("Login OK user_id={} role={}", user.id, user.role.value)
    return user, token, expires_in


def ensure_default_admin(db: Session) -> None:
    """Seed the default admin (librarian) on first boot if none exists."""
    has_admin = db.execute(
        select(User).where(User.role == UserRole.ADMIN).limit(1)
    ).scalar_one_or_none()
    if has_admin is not None:
        return

    admin = User(
        username=settings.default_admin_username,
        email=settings.default_admin_email,
        full_name="Library Administrator",
        hashed_password=hash_password(settings.default_admin_password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info(
        "Default admin seeded — username={} (please change the password!)",
        admin.username,
    )
