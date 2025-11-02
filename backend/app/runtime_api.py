"""API routes for workflow runtime."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from .models.runtime import (
    SessionCreateResponse,
    SessionExecuteRequest,
    WorkflowAppResponse,
    WorkflowSessionResponse,
)
from .workflow_runtime.exceptions import ComponentExecutionError, SessionNotFoundError
from .workflow_runtime.service import WorkflowRuntimeService
from .workflow_runtime.storage import (
    InMemorySessionStore,
    SessionStoreError,
    create_session_store,
)

router = APIRouter(prefix="/api/runtime", tags=["workflow-runtime"])


@lru_cache(maxsize=1)
def get_runtime_service() -> WorkflowRuntimeService:
    workflow_path = Path(os.getenv("WORKFLOW_FILE", "workflow.yaml"))
    raw_redis_url = os.getenv("REDIS_URL")
    if raw_redis_url and raw_redis_url.strip().lower() in {"memory", "memory://"}:
        redis_url: str | None = None
    else:
        redis_url = raw_redis_url or "redis://redis:6379/0"

    try:
        store = create_session_store(redis_url, allow_fallback=False)
    except SessionStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if redis_url and isinstance(store, InMemorySessionStore):
        raise HTTPException(status_code=503, detail="Redis session store unavailable")

    return WorkflowRuntimeService(workflow_path=workflow_path, session_store=store)


@router.get("/workflow", response_model=WorkflowAppResponse)
def fetch_workflow(service: WorkflowRuntimeService = Depends(get_runtime_service)) -> WorkflowAppResponse:
    workflow = service.load_workflow()
    return WorkflowAppResponse(workflow=workflow)


@router.post("/sessions", response_model=SessionCreateResponse)
def create_session(service: WorkflowRuntimeService = Depends(get_runtime_service)) -> SessionCreateResponse:
    session = service.create_session()
    return SessionCreateResponse(
        session_id=session.session_id,
        status=session.status,
        current_step=session.current_step,
        view=service.sanitize_view(session),
        context=service.sanitize_context(session),
    )


@router.get("/sessions/{session_id}", response_model=WorkflowSessionResponse)
def get_session(
    session_id: str,
    service: WorkflowRuntimeService = Depends(get_runtime_service),
) -> WorkflowSessionResponse:
    try:
        session = service.get_session(session_id)
    except SessionNotFoundError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return WorkflowSessionResponse(
        session_id=session.session_id,
        status=session.status,
        current_step=session.current_step,
        view=service.sanitize_view(session),
        context=service.sanitize_context(session),
        error=session.error,
    )


@router.post("/sessions/{session_id}/execute", response_model=WorkflowSessionResponse)
def execute_session(
    session_id: str,
    payload: SessionExecuteRequest,
    service: WorkflowRuntimeService = Depends(get_runtime_service),
) -> WorkflowSessionResponse:
    try:
        session = service.execute_session(session_id, payload.inputs, step_id=payload.step_id)
    except SessionNotFoundError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ComponentExecutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: PERF203
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return WorkflowSessionResponse(
        session_id=session.session_id,
        status=session.status,
        current_step=session.current_step,
        view=service.sanitize_view(session),
        context=service.sanitize_context(session),
        error=session.error,
    )
