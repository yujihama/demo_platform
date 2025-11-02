"""FastAPI router for the workflow runtime engine."""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.datastructures import UploadFile

from pydantic import BaseModel

from ..models.workflow import PipelineSection, UISection, WorkflowInfo
from .engine import WorkflowEngine, get_runtime_engine
from .models import SubmitStepPayload, WorkflowSessionPublicState

router = APIRouter(prefix="/runtime", tags=["runtime"])


class WorkflowDefinitionResponse(BaseModel):
    """Response model bundling workflow metadata and UI definition."""

    info: WorkflowInfo
    ui: Optional[UISection]
    pipeline: PipelineSection


def get_engine() -> WorkflowEngine:
    return get_runtime_engine()


@router.get("/workflow", response_model=WorkflowDefinitionResponse)
async def fetch_workflow(engine: WorkflowEngine = Depends(get_engine)) -> dict:
    workflow = engine.workflow
    return {
        "info": workflow.info,
        "ui": workflow.ui,
        "pipeline": workflow.pipeline,
    }


@router.post("/sessions", response_model=WorkflowSessionPublicState, status_code=status.HTTP_201_CREATED)
async def create_session(engine: WorkflowEngine = Depends(get_engine)) -> WorkflowSessionPublicState:
    return await engine.create_session()


@router.get("/sessions/{session_id}", response_model=WorkflowSessionPublicState)
async def get_session(session_id: str, engine: WorkflowEngine = Depends(get_engine)) -> WorkflowSessionPublicState:
    session = await engine.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="セッションが見つかりません。")
    return session


@router.post("/sessions/{session_id}/steps/{step_id}", response_model=WorkflowSessionPublicState)
async def submit_step(
    session_id: str,
    step_id: str,
    request: Request,
    engine: WorkflowEngine = Depends(get_engine),
) -> WorkflowSessionPublicState:
    file: UploadFile | None = None
    payload_dict: dict

    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        file = form.get("file")  # type: ignore[assignment]
        payload_raw = form.get("payload")
        if isinstance(payload_raw, str):
            payload_dict = json.loads(payload_raw)
        elif isinstance(payload_raw, (bytes, bytearray)):
            payload_dict = json.loads(payload_raw.decode("utf-8"))
        else:
            payload_dict = {}
    else:
        try:
            payload_dict = await request.json()
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSONのパースに失敗しました。") from exc

    payload = SubmitStepPayload.model_validate(payload_dict or {})

    try:
        return await engine.submit_step(session_id, step_id, payload.data, file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - propagate runtime errors
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
