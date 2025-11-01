"""Pydantic models for workflow generation and packaging APIs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .workflow import WorkflowSpecification


class AgentRole(str, Enum):
    ANALYST = "analyst"
    ARCHITECT = "architect"
    SPECIALIST = "specialist"
    VALIDATOR = "validator"


class AgentMessage(BaseModel):
    """Single turn in the multi-agent workflow generation dialogue."""

    role: AgentRole
    title: str
    content: str
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowGenerationRequest(BaseModel):
    """Request payload for generating a workflow from a natural language prompt."""

    prompt: str = Field(..., description="End-user requirements in natural language")
    app_name: Optional[str] = Field(None, description="Optional override for workflow.info.name")
    session_id: Optional[str] = Field(
        None,
        description="Identifier used by the frontend to correlate retries and corrections.",
    )
    force_mock: Optional[bool] = Field(
        None,
        description="If set, overrides configuration to force mock or real LLM provider.",
    )


class WorkflowGenerationResponse(BaseModel):
    """Response containing the generated workflow and supporting metadata."""

    workflow: WorkflowSpecification
    workflow_yaml: str = Field(..., description="YAML representation of the workflow specification")
    messages: List[AgentMessage] = Field(default_factory=list)
    retries: int = 0
    duration_ms: int = 0


class PackageCreateRequest(BaseModel):
    """Request payload for packaging an application for download."""

    workflow_yaml: str
    app_name: str
    include_mock_server: bool = Field(
        True,
        description="Whether to bundle the mock Dify server alongside the runtime compose file.",
    )
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables to render into the .env template.",
    )


class PackageDescriptor(BaseModel):
    """Metadata about a generated package."""

    package_id: str
    filename: str
    download_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    size_bytes: Optional[int] = None


class PackageCreateResponse(BaseModel):
    """Response returned when a package is created."""

    package: PackageDescriptor


class GenerationOptions(BaseModel):
    """Feature flags controlling optional assets produced by the pipeline."""

    include_playwright: bool = True
    include_docker: bool = True
    include_logging: bool = True


class GenerationRequest(BaseModel):
    """Request payload accepted by the legacy generation pipeline."""

    user_id: str
    project_id: str
    project_name: str
    description: str
    mock_spec_id: str
    options: GenerationOptions
    requirements_prompt: Optional[str] = None
    use_mock: Optional[bool] = None


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStatus(str, Enum):
    RECEIVED = "received"
    SPEC_GENERATING = "spec_generating"
    TEMPLATES_RENDERING = "templates_rendering"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"


class JobStep(BaseModel):
    """Single unit of work within a generation job."""

    id: str
    label: str
    status: StepStatus = StepStatus.PENDING
    message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)


class GenerationJob(BaseModel):
    """In-flight job tracked by the pipeline and CLI."""

    job_id: str
    user_id: str
    project_id: str
    project_name: str
    description: str
    status: JobStatus = JobStatus.RECEIVED
    steps: List[JobStep] = Field(default_factory=list)
    download_url: Optional[str] = None
    output_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


__all__ = [
    "AgentRole",
    "AgentMessage",
    "WorkflowGenerationRequest",
    "WorkflowGenerationResponse",
    "PackageCreateRequest",
    "PackageCreateResponse",
    "PackageDescriptor",
    "GenerationOptions",
    "GenerationRequest",
    "GenerationJob",
    "JobStatus",
    "JobStep",
    "StepStatus",
]

