"""Session persistence utilities."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, Protocol

import orjson

try:  # pragma: no cover - optional dependency
    from redis.asyncio import Redis
except ImportError:  # pragma: no cover - fallback when redis is unavailable
    Redis = None  # type: ignore


class BaseSessionStore(Protocol):
    """Protocol for session persistence backends."""

    async def create(self, session_id: str, payload: Dict[str, Any]) -> None:
        ...

    async def update(self, session_id: str, payload: Dict[str, Any]) -> None:
        ...

    async def get(self, session_id: str) -> Dict[str, Any] | None:
        ...

    async def delete(self, session_id: str) -> None:
        ...


class InMemorySessionStore:
    """A threadsafe in-memory session store used for local development/tests."""

    def __init__(self) -> None:
        self._payloads: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create(self, session_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            self._payloads[session_id] = payload

    async def update(self, session_id: str, payload: Dict[str, Any]) -> None:
        async with self._lock:
            self._payloads[session_id] = payload

    async def get(self, session_id: str) -> Dict[str, Any] | None:
        async with self._lock:
            return self._payloads.get(session_id)

    async def delete(self, session_id: str) -> None:
        async with self._lock:
            self._payloads.pop(session_id, None)


class RedisSessionStore:
    """Redis-backed session store used in production deployments."""

    def __init__(self, url: str, ttl_seconds: int = 3600) -> None:
        if Redis is None:  # pragma: no cover - handled during runtime configuration
            raise RuntimeError("redis package not installed")
        self._redis = Redis.from_url(url, encoding="utf-8", decode_responses=False)
        self._ttl = ttl_seconds

    async def create(self, session_id: str, payload: Dict[str, Any]) -> None:
        await self._redis.setex(session_id, self._ttl, orjson.dumps(payload))

    async def update(self, session_id: str, payload: Dict[str, Any]) -> None:
        await self._redis.setex(session_id, self._ttl, orjson.dumps(payload))

    async def get(self, session_id: str) -> Dict[str, Any] | None:
        raw = await self._redis.get(session_id)
        if raw is None:
            return None
        return orjson.loads(raw)

    async def delete(self, session_id: str) -> None:
        await self._redis.delete(session_id)

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:  # pragma: no cover - network failure fallback
            return False


def build_session_store() -> BaseSessionStore:
    """Factory that prefers Redis but gracefully falls back to in-memory storage."""

    redis_url = os.environ.get("REDIS_URL")
    if redis_url and Redis is not None:
        store = RedisSessionStore(redis_url)
        return store
    return InMemorySessionStore()
