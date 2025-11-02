"""API routes for LLM conversation driven workflow generation."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from .models.conversation import (
    ConversationCreateRequest,
    ConversationCreateResponse,
    ConversationStatusResponse,
    PackageResponse,
)
from .models.generation import GenerationRequest, JobStatus
from .services.jobs import job_registry
from .services.workflow_pipeline import WorkflowGenerationPipeline, workflow_pipeline
from .services.conversation_sessions import conversation_sessions, ConversationSessionManager


router = APIRouter(prefix="/api/generate", tags=["conversation"])


def get_workflow_pipeline() -> WorkflowGenerationPipeline:
    return workflow_pipeline


def get_session_manager() -> ConversationSessionManager:
    return conversation_sessions


@router.post("/conversations", response_model=ConversationCreateResponse)
async def create_conversation(
    payload: ConversationCreateRequest,
    background_tasks: BackgroundTasks,
    pipeline: WorkflowGenerationPipeline = Depends(get_workflow_pipeline),
    sessions: ConversationSessionManager = Depends(get_session_manager),
) -> ConversationCreateResponse:
    request = GenerationRequest(
        user_id=payload.user_id,
        project_id=payload.project_id,
        project_name=payload.project_name,
        description=payload.description or payload.prompt,
        requirements_prompt=payload.prompt,
    )
    job = pipeline.enqueue(request, background_tasks)
    session = sessions.create_session(
        job.job_id,
        payload.user_id,
        payload.project_id,
        payload.project_name,
        payload.prompt,
    )
    sessions.update_progress(job.job_id, JobStatus.RECEIVED, "ジョブを登録しました")
    return ConversationCreateResponse(
        session_id=job.job_id,
        status=JobStatus.RECEIVED,
        messages=list(session.messages),
    )


@router.get("/conversations/{session_id}", response_model=ConversationStatusResponse)
async def get_conversation(
    session_id: str,
    sessions: ConversationSessionManager = Depends(get_session_manager),
) -> ConversationStatusResponse:
    session = sessions.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    job = job_registry.get(session_id)
    steps = job.steps if job else []
    download_url = job.download_url if job else None
    return ConversationStatusResponse(
        session_id=session.session_id,
        status=session.status,
        messages=session.messages,
        steps=steps,
        download_url=download_url,
    )


@router.get(
    "/conversations/{session_id}/workflow",
    response_class=PlainTextResponse,
)
async def get_conversation_workflow(
    session_id: str,
    sessions: ConversationSessionManager = Depends(get_session_manager),
) -> PlainTextResponse:
    session = sessions.get_session(session_id)
    if session is None or session.workflow_path is None:
        raise HTTPException(status_code=404, detail="workflow.yaml not available")

    workflow_yaml = session.workflow_path.read_text(encoding="utf-8")
    return PlainTextResponse(content=workflow_yaml, media_type="text/yaml")


@router.get("/conversations/{session_id}/package", response_model=PackageResponse)
async def get_conversation_package(
    session_id: str,
    sessions: ConversationSessionManager = Depends(get_session_manager),
) -> PackageResponse:
    session = sessions.get_session(session_id)
    if session is None or session.package_path is None:
        raise HTTPException(status_code=404, detail="Package not available")

    size = session.package_path.stat().st_size
    return PackageResponse(
        session_id=session.session_id,
        filename=session.package_path.name,
        size_bytes=size,
        updated_at=session.updated_at,
    )


@router.get("/conversations/{session_id}/package/download")
async def download_conversation_package(
    session_id: str,
    sessions: ConversationSessionManager = Depends(get_session_manager),
) -> FileResponse:
    session = sessions.get_session(session_id)
    if session is None or session.package_path is None:
        raise HTTPException(status_code=404, detail="Package not available")

    package_path: Path = session.package_path
    return FileResponse(
        path=package_path,
        filename=package_path.name,
        media_type="application/zip",
    )

