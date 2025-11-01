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


__all__ = [
    "AgentRole",
    "AgentMessage",
    "WorkflowGenerationRequest",
    "WorkflowGenerationResponse",
    "PackageCreateRequest",
    "PackageCreateResponse",
    "PackageDescriptor",
]

