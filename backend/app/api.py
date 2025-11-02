"""API router definitions for the generation backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .config import config_manager
from .models.generation import GenerationRequest, GenerationResponse, GenerationStatusResponse
from .services.jobs import job_registry
from .services.pipeline import GenerationPipeline, pipeline
from .services.workflow_pipeline import WorkflowGenerationPipeline, workflow_pipeline
from .services.preview import MockPreviewService


def _resolve_use_mock(payload: GenerationRequest) -> bool:
    if payload.use_mock is not None:
        return payload.use_mock
    return config_manager.features.agents.use_mock


def get_pipeline() -> GenerationPipeline:
    return pipeline


def get_workflow_pipeline() -> WorkflowGenerationPipeline:
    return workflow_pipeline


preview_service = MockPreviewService(Path("mock/previews"))


router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate", response_model=GenerationResponse)
async def create_generation_job(
    payload: GenerationRequest,
    background_tasks: BackgroundTasks,
    template_pipeline: GenerationPipeline = Depends(get_pipeline),
    declarative_pipeline: WorkflowGenerationPipeline = Depends(get_workflow_pipeline),
) -> GenerationResponse:
    use_mock = _resolve_use_mock(payload)
    if use_mock:
        job = template_pipeline.enqueue(payload, background_tasks)
    else:
        job = declarative_pipeline.enqueue(payload, background_tasks)
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

