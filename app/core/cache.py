"""Tiny Redis cache wrapper that implements the Cache-Aside pattern.

The cache degrades gracefully: if Redis is unreachable, calls become no-ops
so the API stays available (just slower). All log lines are emitted at INFO
or WARNING so a Grafana panel on `cache_*` events is easy to build.
"""
from __future__ import annotations

import json
from typing import Any, Callable

import redis

from app.core.config import settings
from app.core.logging import logger


class CacheClient:
    """Thin wrapper around a redis.Redis instance."""

    def __init__(self, url: str, default_ttl: int):
        self._url = url
        self._default_ttl = default_ttl
        self._client: redis.Redis | None = None
        self._unavailable = False

    def _connect(self) -> redis.Redis | None:
        if self._client is not None or self._unavailable:
            return self._client
        try:
            client = redis.Redis.from_url(
                self._url, decode_responses=True, socket_connect_timeout=1
            )
            client.ping()
            self._client = client
            logger.info("Redis cache connected at {}", self._url)
        except Exception as exc:  # pragma: no cover - depends on env
            self._unavailable = True
            logger.warning("Redis unavailable ({}). Caching disabled.", exc)
        return self._client

    # ---- core ops ---------------------------------------------------- #
    def get(self, key: str) -> Any | None:
        client = self._connect()
        if client is None:
            return None
        try:
            raw = client.get(key)
            if raw is None:
                logger.debug("CACHE MISS  key={}", key)
                return None
            logger.debug("CACHE HIT   key={}", key)
            return json.loads(raw)
        except Exception as exc:  # pragma: no cover
            logger.warning("Cache get failed for {}: {}", key, exc)
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        client = self._connect()
        if client is None:
            return
        try:
            client.set(key, json.dumps(value, default=str), ex=ttl or self._default_ttl)
            logger.debug("CACHE SET   key={} ttl={}", key, ttl or self._default_ttl)
        except Exception as exc:  # pragma: no cover
            logger.warning("Cache set failed for {}: {}", key, exc)

    def delete_pattern(self, pattern: str) -> int:
        """Delete every key matching ``pattern`` (e.g. ``books:*``)."""
        client = self._connect()
        if client is None:
            return 0
        try:
            keys = list(client.scan_iter(match=pattern))
            if not keys:
                return 0
            n = client.delete(*keys)
            logger.info("CACHE INVALIDATE pattern={} removed={}", pattern, n)
            return n
        except Exception as exc:  # pragma: no cover
            logger.warning("Cache invalidate failed for {}: {}", pattern, exc)
            return 0

    def get_or_set(
        self, key: str, loader: Callable[[], Any], ttl: int | None = None
    ) -> Any:
        """Cache-aside helper. Returns the cached value or loads, stores, returns."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = loader()
        if value is not None:
            self.set(key, value, ttl)
        return value


# Global instance used by services.
cache = CacheClient(settings.redis_url, settings.cache_ttl_seconds)


__all__ = ["cache", "CacheClient"]
