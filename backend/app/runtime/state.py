"""State persistence helpers for workflow runtime sessions."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Optional

from redis.asyncio import Redis

from .models import WorkflowSession


class StateStoreProtocol:
    """Protocol-like base class for state stores."""

    async def create(self, session: WorkflowSession, ttl: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def load(self, session_id: str) -> Optional[WorkflowSession]:  # pragma: no cover - interface
        raise NotImplementedError

    async def save(self, session: WorkflowSession, ttl: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def delete(self, session_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class RedisStateStore(StateStoreProtocol):
    """Redis-backed store for workflow sessions."""

    def __init__(self, redis: Redis, namespace: str = "workflow") -> None:
        self._redis = redis
        self._namespace = namespace

    def _key(self, session_id: str) -> str:
        return f"{self._namespace}:session:{session_id}"

    async def create(self, session: WorkflowSession, ttl: int) -> None:
        payload = session.model_dump(mode="json")
        await self._redis.set(self._key(session.session_id), json.dumps(payload), ex=ttl)

    async def load(self, session_id: str) -> Optional[WorkflowSession]:
        raw = await self._redis.get(self._key(session_id))
        if raw is None:
            return None
        data = json.loads(raw)
        return WorkflowSession.model_validate(data)

    async def save(self, session: WorkflowSession, ttl: int) -> None:
        payload = session.model_dump(mode="json")
        await self._redis.set(self._key(session.session_id), json.dumps(payload), ex=ttl)

    async def delete(self, session_id: str) -> None:
        await self._redis.delete(self._key(session_id))


class InMemoryStateStore(StateStoreProtocol):
    """Simple in-memory store useful for tests and development."""

    def __init__(self) -> None:
        self._store: Dict[str, WorkflowSession] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    async def create(self, session: WorkflowSession, ttl: int) -> None:
        self._store[session.session_id] = session
        self._locks.setdefault(session.session_id, asyncio.Lock())

    async def load(self, session_id: str) -> Optional[WorkflowSession]:
        session = self._store.get(session_id)
        if session is None:
            return None
        # Return a copy to avoid accidental mutation without save()
        return WorkflowSession.model_validate(session.model_dump())

    async def save(self, session: WorkflowSession, ttl: int) -> None:
        self._store[session.session_id] = session
        self._locks.setdefault(session.session_id, asyncio.Lock())

    async def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)
        self._locks.pop(session_id, None)

    async def acquire_lock(self, session_id: str) -> asyncio.Lock:
        lock = self._locks.setdefault(session_id, asyncio.Lock())
        await lock.acquire()
        return lock
