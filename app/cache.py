"""
Lightweight Redis cache helper for Legend AI API.

Fail-open if Redis is not configured. Provides JSON helpers with TTL.
"""

import json
import os
import typing as t

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover - optional dep
    redis = None  # type: ignore


REDIS_URL = os.getenv("REDIS_URL")
_client = None
if REDIS_URL and redis:
    _client = redis.Redis.from_url(REDIS_URL)


def cache_get(key: str) -> t.Any:
    if not _client:
        return None
    value = _client.get(key)
    return json.loads(value) if value else None


def cache_set(key: str, data: t.Any, ttl: int = 60) -> None:
    if not _client:
        return
    _client.setex(key, ttl, json.dumps(data))
