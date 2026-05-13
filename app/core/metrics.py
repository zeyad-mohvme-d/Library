"""Prometheus metrics setup using prometheus-fastapi-instrumentator."""
from __future__ import annotations

from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator


# Custom business metrics
borrow_counter = Counter(
    "library_borrow_total",
    "Total number of successful borrow operations.",
    labelnames=("status",),  # success / denied
)

return_counter = Counter(
    "library_return_total",
    "Total number of successful return operations.",
)

auth_counter = Counter(
    "library_auth_attempts_total",
    "Login/registration attempts by outcome.",
    labelnames=("event", "result"),  # event: login|register, result: success|failure
)

cache_hits = Counter(
    "library_cache_events_total",
    "Cache hit/miss/invalidation events.",
    labelnames=("event",),  # hit | miss | invalidate
)

db_query_latency = Histogram(
    "library_db_query_seconds",
    "Database query duration in seconds.",
    labelnames=("operation",),
)


def setup_metrics(app):
    """Attach Prometheus instrumentation and expose ``/metrics``."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", "/health"],
    )
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


__all__ = [
    "setup_metrics",
    "borrow_counter",
    "return_counter",
    "auth_counter",
    "cache_hits",
    "db_query_latency",
]
