"""Session state storage abstraction."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional

try:
    from redis import asyncio as redis_async
except Exception:  # pragma: no cover - optional dependency
    redis_async = None  # type: ignore

from .config import runtime_config
from .models import ComponentState, SessionState

logger = logging.getLogger(__name__)


class RuntimeStateStore:
    """Abstract interface for session state persistence."""

    async def create_session(self, state: SessionState) -> SessionState:
        raise NotImplementedError

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        raise NotImplementedError

    async def save_session(self, state: SessionState) -> SessionState:
        raise NotImplementedError


class InMemoryStateStore(RuntimeStateStore):
    """Simple in-memory store used when Redis is unavailable."""

    def __init__(self) -> None:
        self._store: Dict[str, SessionState] = {}
        self._lock = asyncio.Lock()

    async def create_session(self, state: SessionState) -> SessionState:
        async with self._lock:
            state.created_at = datetime.utcnow()
            state.updated_at = state.created_at
            self._store[state.session_id] = state
            return state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        async with self._lock:
            return self._store.get(session_id)

    async def save_session(self, state: SessionState) -> SessionState:
        async with self._lock:
            state.updated_at = datetime.utcnow()
            self._store[state.session_id] = state
            return state


class RedisStateStore(RuntimeStateStore):
    """Redis-backed session store."""

    def __init__(self, url: str, ttl_seconds: int) -> None:
        if redis_async is None:
            raise RuntimeError("redis package is required for RedisStateStore")
        self._redis = redis_async.from_url(url, encoding="utf-8", decode_responses=True)
        self._ttl = ttl_seconds

    async def create_session(self, state: SessionState) -> SessionState:
        await self.save_session(state)
        return state

    async def get_session(self, session_id: str) -> Optional[SessionState]:
        payload = await self._redis.get(self._key(session_id))
        if payload is None:
            return None
        data = json.loads(payload)
        data["component_state"] = {
            key: ComponentState(**value) for key, value in data.get("component_state", {}).items()
        }
        return SessionState(**data)

    async def save_session(self, state: SessionState) -> SessionState:
        state.updated_at = datetime.utcnow()
        serialisable = json.loads(state.model_dump_json())
        await self._redis.set(self._key(state.session_id), json.dumps(serialisable, ensure_ascii=False), ex=self._ttl)
        return state

    def _key(self, session_id: str) -> str:
        return f"runtime:session:{session_id}"


async def initialise_state_store() -> RuntimeStateStore:
    """Initialise the most appropriate state store."""

    cfg = runtime_config()
    if cfg.redis_url and redis_async is not None:
        try:
            client = redis_async.from_url(cfg.redis_url, encoding="utf-8", decode_responses=True)
            await client.ping()
            logger.info("Using Redis state store", extra={"url": cfg.redis_url})
            return RedisStateStore(cfg.redis_url, cfg.session_ttl_seconds)
        except Exception as exc:  # pragma: no cover - connection failure fallback
            logger.warning("Redis unavailable, falling back to in-memory store", exc_info=exc)
    else:
        if cfg.redis_url:
            logger.warning("redis package not installed; falling back to in-memory store")
    return InMemoryStateStore()


