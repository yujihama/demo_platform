"""API router definitions for the generation backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse

from .config import config_manager
from .models.conversation import ConversationCreateRequest, ConversationSessionResponse
from .models.generation import GenerationRequest, GenerationResponse, GenerationStatusResponse
from .services.conversation import ConversationService, conversation_service
from .services.jobs import job_registry
from .services.pipeline import GenerationPipeline, pipeline
from .services.preview import MockPreviewService


def get_pipeline() -> GenerationPipeline:
    return pipeline


def get_conversation_service() -> ConversationService:
    return conversation_service


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


@router.post("/generate/conversations", response_model=ConversationSessionResponse)
async def start_conversation(
    payload: ConversationCreateRequest,
    background_tasks: BackgroundTasks,
    service: ConversationService = Depends(get_conversation_service),
) -> ConversationSessionResponse:
    return service.start(payload, background_tasks)


@router.get("/generate/conversations/{session_id}", response_model=ConversationSessionResponse)
async def get_conversation(session_id: str, service: ConversationService = Depends(get_conversation_service)) -> ConversationSessionResponse:
    try:
        return service.get(session_id)
    except KeyError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/generate/conversations/{session_id}/workflow", response_class=PlainTextResponse)
async def get_conversation_workflow(
    session_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> PlainTextResponse:
    try:
        content = service.get_workflow_yaml(session_id)
    except KeyError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(content, media_type="text/yaml")


@router.post("/generate/conversations/{session_id}/package")
async def download_conversation_package(
    session_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> FileResponse:
    try:
        package_path = service.package(session_id)
    except KeyError as exc:  # noqa: PERF203
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = Path(package_path).name
    return FileResponse(path=package_path, filename=filename, media_type="application/zip")

