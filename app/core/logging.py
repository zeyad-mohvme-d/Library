"""Structured logging using loguru.

Logs go to stdout (JSON when not in debug) and a rotating file in ``logs/``.
The ``configure_logging`` function should be called once at app startup.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


class _InterceptHandler(logging.Handler):
    """Forward standard-library log records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - thin wrapper
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging() -> None:
    """Configure loguru sinks and re-route stdlib + uvicorn logs to loguru."""
    logger.remove()

    # Pretty console sink for dev, JSON for everything else.
    if settings.debug:
        logger.add(
            sys.stdout,
            level="DEBUG",
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level:<8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
        )
    else:
        logger.add(sys.stdout, level="INFO", serialize=True)

    # Rotating JSON file sink — useful for log shippers / dashboards.
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "app.log",
        level="INFO",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        serialize=True,
        enqueue=True,
    )

    # Re-route stdlib / uvicorn loggers into loguru.
    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi", "sqlalchemy.engine"):
        logging.getLogger(noisy).handlers = [_InterceptHandler()]
        logging.getLogger(noisy).propagate = False


__all__ = ["configure_logging", "logger"]
