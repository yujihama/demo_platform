"""API router definitions for the generation backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from .config import config_manager
from .models.conversation import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationStatusResponse,
)
from .models.generation import GenerationRequest, GenerationResponse, GenerationStatusResponse
from .services.jobs import job_registry
from .services.pipeline import GenerationPipeline, pipeline
from .services.conversation import conversation_service
from .services.distribution import distribution_service
from .services.preview import MockPreviewService


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


@router.post("/generate/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    payload: ConversationCreateRequest,
) -> ConversationCreateResponse:
    session = conversation_service.create_session(payload)
    return ConversationCreateResponse(
        session_id=session.session_id,
        status=session.status,
        messages=session.messages,
        workflow_ready=session.workflow_path is not None,
    )


@router.get("/generate/conversations/{session_id}", response_model=ConversationStatusResponse)
async def get_conversation(session_id: str) -> ConversationStatusResponse:
    session = conversation_service.require_session(session_id)
    return ConversationStatusResponse(
        session_id=session.session_id,
        status=session.status,
        messages=session.messages,
        workflow_ready=session.workflow_path is not None,
        created_at=session.created_at,
        updated_at=session.updated_at,
        error=session.error,
    )


@router.get("/generate/conversations/{session_id}/workflow", response_class=PlainTextResponse)
async def get_conversation_workflow(session_id: str) -> PlainTextResponse:
    session = conversation_service.require_session(session_id)
    if session.workflow_path is None:
        raise HTTPException(status_code=404, detail="workflow.yaml はまだ生成されていません")
    yaml_text = session.workflow_path.read_text(encoding="utf-8")
    return PlainTextResponse(content=yaml_text, media_type="text/yaml")


@router.post("/generate/conversations/{session_id}/package")
async def create_package(session_id: str) -> FileResponse:
    session = conversation_service.require_session(session_id)
    try:
        archive_path = distribution_service.build_archive(session)
    except ValueError as exc:  # noqa: PERF203
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(
        path=archive_path,
        filename="workflow-package.zip",
        media_type="application/zip",
    )

