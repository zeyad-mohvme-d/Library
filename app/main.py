"""FastAPI application factory.

Run with::

    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger
from app.core.metrics import setup_metrics
from app.core.middleware import RequestLogMiddleware
from app.db.session import Base, SessionLocal, engine
from app.services.user_service import ensure_default_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App startup/shutdown hooks: create tables, seed admin."""
    configure_logging()
    logger.info("Booting {} ({} env)", settings.app_name, settings.app_env)

    # Import models so SQLAlchemy registers them, then create tables.
    from app.models import Book, BorrowRecord, User  # noqa: F401  (side-effect)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        ensure_default_admin(db)

    yield
    logger.info("Shutting down {}", settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Library Management System — Project 2.\n\n"
            "FastAPI + MySQL + Redis + JWT + Prometheus/Grafana."
        ),
        lifespan=lifespan,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS — open by default in dev, scoped via env in prod.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id", "x-process-time-ms"],
    )
    app.add_middleware(RequestLogMiddleware)

    # Exception handlers, Prometheus, routes
    register_exception_handlers(app)
    setup_metrics(app)
    app.include_router(api_router)

    @app.get("/", tags=["Health"], summary="Service banner")
    def root():
        return {
            "name": settings.app_name,
            "status": "ok",
            "docs": "/docs",
            "metrics": "/metrics",
            "health": "/health",
        }

    @app.get("/health", tags=["Health"], summary="Liveness probe")
    def health():
        return {"status": "healthy", "env": settings.app_env}

    return app


app = create_app()
