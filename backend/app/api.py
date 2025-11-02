"""API router definitions for the generation backend."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .config import config_manager
from .models.generation import (
    ConversationRequest,
    ConversationResponse,
    ConversationStatusResponse,
    GenerationRequest,
    GenerationJob,
    GenerationResponse,
    GenerationStatusResponse,
    JobStatus,
    WorkflowResponse,
)
from .services.conversation_storage import conversation_storage
from .services.jobs import job_registry
from .services.pipeline import GenerationPipeline, pipeline
from .services.preview import MockPreviewService
from .services.workflow_pipeline import workflow_pipeline


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


# Conversation API endpoints
@router.post("/generate/conversations", response_model=ConversationResponse)
async def create_conversation(
    payload: ConversationRequest,
    background_tasks: BackgroundTasks,
) -> ConversationResponse:
    """Create a new conversation session and start workflow generation."""
    session_id = conversation_storage.create_session(
        user_prompt=payload.prompt,
        user_id=payload.user_id,
    )
    
    # Create a GenerationRequest from the conversation prompt
    from uuid import uuid4
    
    generation_request = GenerationRequest(
        user_id=payload.user_id,
        project_id=f"conversation-{session_id[:8]}",
        project_name=f"Generated from conversation",
        description=payload.prompt,
        requirements_prompt=payload.prompt,
        use_mock=False,  # Use LLM pipeline for conversations
    )
    
    # Start workflow generation in background
    def _generate_workflow():
        try:
            conversation_storage.update_status(session_id, "generating")
            job = workflow_pipeline.run_sync(generation_request)
            
            # Extract workflow.yaml from job metadata
            workflow_yaml = None
            if job.metadata and "workflow_yaml" in job.metadata:
                workflow_yaml = job.metadata["workflow_yaml"]
            
            if workflow_yaml:
                conversation_storage.save_workflow_yaml(session_id, workflow_yaml)
                conversation_storage.add_message(
                    session_id,
                    "assistant",
                    "workflow.yaml???????????",
                )
            else:
                conversation_storage.update_status(session_id, "failed")
                conversation_storage.add_message(
                    session_id,
                    "assistant",
                    "workflow.yaml???????????",
                )
        except Exception as e:
            conversation_storage.update_status(session_id, "failed")
            conversation_storage.add_message(
                session_id,
                "assistant",
                f"??????????: {str(e)}",
            )
    
    background_tasks.add_task(_generate_workflow)
    conversation_storage.add_message(
        session_id,
        "assistant",
        "workflow.yaml??????????????????????...",
    )
    
    return ConversationResponse(
        session_id=session_id,
        status="generating",
        message="?????????",
    )


@router.get("/generate/conversations/{session_id}", response_model=ConversationStatusResponse)
async def get_conversation_status(session_id: str) -> ConversationStatusResponse:
    """Get conversation status and messages."""
    session = conversation_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = [
        {"role": msg["role"], "content": msg["content"], "timestamp": msg.get("timestamp")}
        for msg in session.get("messages", [])
    ]
    
    return ConversationStatusResponse(
        session_id=session_id,
        status=session.get("status", "unknown"),
        messages=messages,
        workflow_ready=bool(session.get("workflow_yaml")),
    )


@router.get("/generate/conversations/{session_id}/workflow", response_model=WorkflowResponse)
async def get_conversation_workflow(session_id: str) -> WorkflowResponse:
    """Get generated workflow.yaml for a conversation session."""
    workflow_yaml = conversation_storage.get_workflow_yaml(session_id)
    if not workflow_yaml:
        raise HTTPException(
            status_code=404,
            detail="Workflow not ready. Generation may still be in progress.",
        )
    
    return WorkflowResponse(
        session_id=session_id,
        workflow_yaml=workflow_yaml,
    )


@router.get("/generate/conversations/{session_id}/download")
async def download_conversation_package(session_id: str) -> FileResponse:
    """Download packaged workflow application as zip file."""
    workflow_yaml = conversation_storage.get_workflow_yaml(session_id)
    if not workflow_yaml:
        raise HTTPException(
            status_code=404,
            detail="Workflow not ready. Generation may still be in progress.",
        )
    
    session = conversation_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create a temporary GenerationRequest for packaging
    from uuid import uuid4
    from .services.jobs import job_registry
    
    temp_job_id = str(uuid4())
    generation_request = GenerationRequest(
        user_id=session.get("user_id", "default"),
        project_id=f"conversation-{session_id[:8]}",
        project_name="Generated from conversation",
        description=session.get("messages", [{}])[0].get("content", "") if session.get("messages") else "",
        requirements_prompt=session.get("messages", [{}])[0].get("content", "") if session.get("messages") else "",
    )
    
    # Create a temporary job for packaging
    temp_job = GenerationJob(
        job_id=temp_job_id,
        user_id=generation_request.user_id,
        project_id=generation_request.project_id,
        project_name=generation_request.project_name,
        description=generation_request.description,
        status=JobStatus.COMPLETED,
        steps=[],
        metadata={"workflow_yaml": workflow_yaml},
    )
    job_registry._jobs[temp_job_id] = temp_job  # pylint: disable=protected-access
    
    # Package the workflow
    from .services.workflow_packaging import WorkflowPackagingService
    from pathlib import Path
    from .config import config_manager
    
    packaging_service = WorkflowPackagingService(
        Path(config_manager.features.generation.output_root)
    )
    
    metadata = {
        "workflow_yaml": workflow_yaml,
        "session_id": session_id,
    }
    
    zip_path = packaging_service.package_workflow_app(
        temp_job,
        workflow_yaml,
        metadata,
    )
    
    # Clean up temporary job
    del job_registry._jobs[temp_job_id]  # pylint: disable=protected-access
    
    return FileResponse(
        path=zip_path,
        filename=f"workflow-app-{session_id[:8]}.zip",
        media_type="application/zip",
    )

