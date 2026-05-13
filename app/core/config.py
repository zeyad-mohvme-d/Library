"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration. Pulled from .env / environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Library Management System"
    app_env: str = "development"
    debug: bool = True

    # Database
    database_url: str = "sqlite:///./library.db"

    # JWT
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Redis / Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 60

    # Library policy
    max_borrow_per_user: int = 5
    default_borrow_days: int = 14

    # Default admin
    default_admin_username: str = "admin"
    default_admin_email: str = "admin@library.example.com"
    default_admin_password: str = "Admin@12345"

    # CORS
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value):
        if isinstance(value, str):
            return [o.strip() for o in value.split(",") if o.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read once per process."""
    return Settings()


settings = get_settings()
