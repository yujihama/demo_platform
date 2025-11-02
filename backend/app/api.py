"""API router definitions for the generation backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from .config import config_manager
from .models.conversation import (
    ConversationStartRequest,
    ConversationStartResponse,
    ConversationStatusResponse,
)
from .models.generation import GenerationRequest, GenerationResponse, GenerationStatusResponse
from .services.jobs import job_registry
from .services.pipeline import GenerationPipeline, pipeline
from .services.preview import MockPreviewService
from .services.conversations import conversation_manager


def get_pipeline() -> GenerationPipeline:
    return pipeline


preview_service = MockPreviewService(Path("mock/previews"))


router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=GenerationResponse)
async def create_generation_job(
    payload: GenerationRequest,
    background_tasks: BackgroundTasks,
    pipeline: GenerationPipeline = Depends(get_pipeline),
) -> GenerationResponse:
    job = pipeline.enqueue(payload, background_tasks)
    return GenerationResponse(job_id=job.job_id, status=job.status)


@router.get("/generate/{job_id}", response_model=GenerationStatusResponse)
async def get_generation_job(job_id: str) -> GenerationStatusResponse:
    job = job_registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return GenerationStatusResponse(
        job_id=job.job_id,
        status=job.status,
        steps=job.steps,
        download_url=job.download_url,
        metadata=job.metadata or None,
    )


@router.get("/generate/{job_id}/download")
async def download_artifact(job_id: str) -> FileResponse:
    job = job_registry.get(job_id)
    if job is None or not job.output_path:
        raise HTTPException(status_code=404, detail="Artifact not ready")
    return FileResponse(path=job.output_path, filename="app.zip", media_type="application/zip")


@router.get("/preview/{spec_id}")
async def get_preview(spec_id: str) -> HTMLResponse:
    try:
        html = preview_service.get_preview_html(spec_id)
    except FileNotFoundError as exc:  # noqa: PERF203 - explicit mapping
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return HTMLResponse(content=html)


@router.get("/config/features")
async def get_features_config() -> dict:
    return config_manager.features.model_dump()


@router.post("/generate/conversations", response_model=ConversationStartResponse)
async def start_conversation(
    payload: ConversationStartRequest,
    background_tasks: BackgroundTasks,
) -> ConversationStartResponse:
    try:
        return conversation_manager.start_conversation(payload, background_tasks)
    except Exception as exc:  # noqa: PERF203 - 予期しない例外を明示的に返却
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/generate/conversations/{session_id}", response_model=ConversationStatusResponse)
async def get_conversation(session_id: str) -> ConversationStatusResponse:
    try:
        return conversation_manager.get_session(session_id)
    except KeyError as exc:  # noqa: PERF203 - 存在しない場合
        raise HTTPException(status_code=404, detail="Conversation not found") from exc


@router.get("/generate/conversations/{session_id}/workflow", response_class=PlainTextResponse)
async def get_conversation_workflow(session_id: str) -> PlainTextResponse:
    try:
        workflow = conversation_manager.get_workflow(session_id)
    except KeyError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail="Conversation not found") from exc
    except FileNotFoundError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(workflow.workflow, media_type="application/x-yaml")


@router.get("/generate/conversations/{session_id}/package")
async def download_conversation_package(session_id: str) -> FileResponse:
    try:
        status = conversation_manager.get_session(session_id)
    except KeyError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail="Conversation not found") from exc

    job = job_registry.get(status.job_id)
    if job is None or not job.output_path:
        raise HTTPException(status_code=404, detail="Package not ready")
    return FileResponse(path=job.output_path, filename="app.zip", media_type="application/zip")

