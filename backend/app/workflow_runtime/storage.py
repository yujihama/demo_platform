"""Session storage backends."""

from __future__ import annotations

from typing import Dict, Optional

import orjson

from .session import WorkflowSession

try:
    import redis
except Exception:  # pragma: no cover - redis optional in tests
    redis = None  # type: ignore


class SessionStoreError(RuntimeError):
    """Raised when a session store cannot be initialized."""


class SessionStore:
    """Abstract store for workflow sessions."""

    def save(self, session: WorkflowSession) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def load(self, session_id: str) -> Optional[WorkflowSession]:  # pragma: no cover - interface
        raise NotImplementedError

    def delete(self, session_id: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """Simple in-memory store used for development and tests."""

    def __init__(self) -> None:
        self._sessions: Dict[str, WorkflowSession] = {}

    def save(self, session: WorkflowSession) -> None:
        self._sessions[session.session_id] = session

    def load(self, session_id: str) -> Optional[WorkflowSession]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


class RedisSessionStore(SessionStore):
    """Redis-backed session store."""

    def __init__(self, client: "redis.Redis", *, namespace: str = "workflow:sessions") -> None:
        self._client = client
        self._namespace = namespace

    def save(self, session: WorkflowSession) -> None:
        key = self._key(session.session_id)
        payload = orjson.dumps(session.to_dict())
        self._client.set(key, payload)

    def load(self, session_id: str) -> Optional[WorkflowSession]:
        key = self._key(session_id)
        payload = self._client.get(key)
        if not payload:
            return None
        data = orjson.loads(payload)
        session = WorkflowSession.from_dict(data)
        return session

    def delete(self, session_id: str) -> None:
        key = self._key(session_id)
        self._client.delete(key)

    def _key(self, session_id: str) -> str:
        return f"{self._namespace}:{session_id}"


def create_session_store(
    redis_url: Optional[str] = None,
    *,
    allow_fallback: bool = True,
) -> SessionStore:
    """Create a session store using Redis when available."""

    if redis_url:
        if redis is None:
            if allow_fallback:
                return InMemorySessionStore()
            raise SessionStoreError("redis package not installed")
        try:
            client = redis.Redis.from_url(redis_url, decode_responses=False)
            client.ping()
            return RedisSessionStore(client)
        except Exception as exc:  # pragma: no cover - fallback when redis unavailable
            if allow_fallback:
                return InMemorySessionStore()
            raise SessionStoreError("unable to connect to Redis") from exc
    return InMemorySessionStore()
