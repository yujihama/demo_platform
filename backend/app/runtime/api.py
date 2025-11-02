"""Runtime API router for workflow execution."""

from __future__ import annotations

import base64
from typing import Any, Dict

import yaml
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..models.workflow import WorkflowYaml
from .components import build_component_registry
from .config import runtime_config
from .engine import ExecutionEngine
from .expressions import to_serialisable
from .models import AdvanceRequest, ComponentState, ComponentValueUpdate, SessionActionResponse, SessionCreateResponse, SessionState
from .state import RuntimeStateStore, initialise_state_store


router = APIRouter(prefix="/api/runtime", tags=["runtime"])


async def get_state_store() -> RuntimeStateStore:
    if not hasattr(get_state_store, "_store"):
        get_state_store._store = await initialise_state_store()  # type: ignore[attr-defined]
    return get_state_store._store  # type: ignore[attr-defined]


async def get_engine(store: RuntimeStateStore = Depends(get_state_store)) -> ExecutionEngine:
    if not hasattr(get_engine, "_engine"):
        cfg = runtime_config()
        try:
            payload = cfg.workflow_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise HTTPException(status_code=500, detail=f"workflow.yaml not found at {cfg.workflow_path}") from exc
        data = WorkflowYaml(**yaml.safe_load(payload))  # type: ignore[name-defined]
        get_engine._engine = ExecutionEngine(data, store, build_component_registry())  # type: ignore[attr-defined]
    return get_engine._engine  # type: ignore[attr-defined]


@router.get("/workflow", response_model=Dict[str, Any])
async def get_workflow(engine: ExecutionEngine = Depends(get_engine)) -> Dict[str, Any]:
    return to_serialisable(engine.workflow.model_dump())


@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(engine: ExecutionEngine = Depends(get_engine)) -> SessionCreateResponse:
    session = await engine.create_session()
    return SessionCreateResponse(session=session, workflow=to_serialisable(engine.workflow.model_dump()))


async def _get_session(session_id: str, engine: ExecutionEngine) -> SessionState:
    session = await engine.load_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/sessions/{session_id}", response_model=SessionActionResponse)
async def get_session_state(session_id: str, engine: ExecutionEngine = Depends(get_engine)) -> SessionActionResponse:
    session = await _get_session(session_id, engine)
    return SessionActionResponse(session=session)


@router.post("/sessions/{session_id}/advance", response_model=SessionActionResponse)
async def advance_session(
    session_id: str,
    payload: AdvanceRequest,
    engine: ExecutionEngine = Depends(get_engine),
) -> SessionActionResponse:
    _ = payload.step_id
    session = await _get_session(session_id, engine)
    session = await engine.advance(session)
    return SessionActionResponse(session=session)


@router.post("/sessions/{session_id}/components/{component_id}", response_model=SessionActionResponse)
async def update_component_value(
    session_id: str,
    component_id: str,
    update: ComponentValueUpdate,
    engine: ExecutionEngine = Depends(get_engine),
) -> SessionActionResponse:
    session = await _get_session(session_id, engine)
    session.component_state[component_id] = ComponentState(value=to_serialisable(update.value), status="ready")
    session = await engine.save_session(session)
    return SessionActionResponse(session=session)


@router.post("/sessions/{session_id}/components/{component_id}/upload", response_model=SessionActionResponse)
async def upload_component_value(
    session_id: str,
    component_id: str,
    file: UploadFile = File(...),
    engine: ExecutionEngine = Depends(get_engine),
) -> SessionActionResponse:
    session = await _get_session(session_id, engine)
    content = await file.read()
    encoded = base64.b64encode(content).decode("utf-8")
    session.component_state[component_id] = ComponentState(
        value={
            "filename": file.filename,
            "content_type": file.content_type,
            "data": encoded,
        },
        status="ready",
    )
    session = await engine.save_session(session)
    return SessionActionResponse(session=session)


