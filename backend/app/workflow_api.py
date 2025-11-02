"""FastAPI routes for executing workflow.yaml applications."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from .logging import logger
from .models.runtime import (
    ErrorResponse,
    ExecuteResponse,
    SessionCreateResponse,
    SessionStateResponse,
    WorkflowDefinitionResponse,
)
from .runtime.engine import WorkflowEngine, build_engine
from .runtime.errors import MissingInputError, UnknownComponentError, WorkflowRuntimeError

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


def get_engine() -> WorkflowEngine:
    return build_engine()


@router.get("/definition", response_model=WorkflowDefinitionResponse)
async def get_workflow_definition(engine: WorkflowEngine = Depends(get_engine)) -> WorkflowDefinitionResponse:
    return WorkflowDefinitionResponse(workflow=engine.workflow)


@router.post("/sessions", response_model=SessionCreateResponse)
async def create_session(engine: WorkflowEngine = Depends(get_engine)) -> SessionCreateResponse:
    context = await engine.create_session()
    return SessionCreateResponse(session=context.to_model())


@router.get(
    "/sessions/{session_id}",
    response_model=SessionStateResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_session(session_id: str, engine: WorkflowEngine = Depends(get_engine)) -> SessionStateResponse:
    context = await engine.get_session(session_id)
    if context is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return SessionStateResponse(session=context.to_model())


@router.post(
    "/sessions/{session_id}/inputs/{step_id}",
    response_model=SessionStateResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def upload_input(
    session_id: str,
    step_id: str,
    file: UploadFile = File(...),
    engine: WorkflowEngine = Depends(get_engine),
) -> SessionStateResponse:
    try:
        context = await engine.store_file_input(session_id, step_id, file)
    except WorkflowRuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SessionStateResponse(session=context.to_model())


@router.post(
    "/sessions/{session_id}/execute",
    response_model=ExecuteResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def execute_pipeline(session_id: str, engine: WorkflowEngine = Depends(get_engine)) -> ExecuteResponse:
    try:
        context = await engine.execute(session_id)
    except MissingInputError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except UnknownComponentError as exc:
        logger.exception("Unknown component in workflow pipeline: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except WorkflowRuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ExecuteResponse(session=context.to_model())
