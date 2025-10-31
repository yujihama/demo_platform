"""Pydantic models for the generation API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class JobStatus(str, Enum):
    RECEIVED = "received"
    SPEC_GENERATING = "spec_generating"
    TEMPLATES_RENDERING = "templates_rendering"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationOptions(BaseModel):
    include_playwright: bool = True
    include_docker: bool = True
    include_logging: bool = True


class GenerationRequest(BaseModel):
    user_id: str = Field(..., description="Identifier of the requesting user")
    project_id: str = Field(..., description="Project identifier for output grouping")
    project_name: str = Field(..., description="Display name of the generated project")
    description: str = Field(..., description="High level description of the app to generate")
    mock_spec_id: str = Field("invoice-verification", description="Mock specification ID")
    options: GenerationOptions = Field(default_factory=GenerationOptions)


class JobStep(BaseModel):
    id: str
    label: str
    status: StepStatus
    message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class GenerationJob(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    job_id: str
    user_id: str
    project_id: str
    project_name: str
    description: str
    status: JobStatus
    steps: List[JobStep]
    download_url: Optional[str] = None
    output_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class GenerationResponse(BaseModel):
    job_id: str
    status: JobStatus


class GenerationStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    steps: List[JobStep]
    download_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

