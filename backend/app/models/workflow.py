"""Pydantic models for workflow.yaml schema."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


class WorkflowInfo(BaseModel):
    """Application metadata section."""
    name: str = Field(..., description="Application name")
    description: str = Field(..., description="Application description")
    version: str = Field(default="1.0.0", description="Application version")
    author: Optional[str] = Field(default=None, description="Application author")


class WorkflowProvider(BaseModel):
    """Workflow provider configuration."""
    provider: Literal["dify", "mock"] = Field(..., description="Provider type")
    endpoint: str = Field(..., description="API endpoint URL")
    api_key_env: Optional[str] = Field(default=None, description="Environment variable name for API key")


class UIComponent(BaseModel):
    """Base UI component definition."""
    type: str = Field(..., description="Component type (table, file_upload, button, etc.)")
    id: str = Field(..., description="Component unique identifier")
    props: Dict[str, Any] = Field(default_factory=dict, description="Component properties")


class UIStep(BaseModel):
    """UI step definition."""
    id: str = Field(..., description="Step unique identifier")
    title: str = Field(..., description="Step title")
    description: Optional[str] = Field(default=None, description="Step description")
    components: List[UIComponent] = Field(default_factory=list, description="Components in this step")


class UISection(BaseModel):
    """UI section defining the frontend layout."""
    layout: str = Field(default="wizard", description="Layout type (wizard, single, etc.)")
    steps: List[UIStep] = Field(default_factory=list, description="UI steps")


class PipelineStep(BaseModel):
    """Pipeline step definition."""
    id: str = Field(..., description="Step unique identifier")
    component: str = Field(..., description="Component name to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Component parameters")
    condition: Optional[str] = Field(default=None, description="Conditional execution expression")
    on_error: Optional[str] = Field(default=None, description="Error handling strategy")


class PipelineSection(BaseModel):
    """Pipeline section defining backend processing flow."""
    steps: List[PipelineStep] = Field(default_factory=list, description="Processing steps")


class WorkflowYaml(BaseModel):
    """Complete workflow.yaml schema."""
    info: WorkflowInfo = Field(..., description="Application metadata")
    workflows: Dict[str, WorkflowProvider] = Field(
        ..., description="Workflow providers configuration"
    )
    ui: Optional[UISection] = Field(default=None, description="UI definition")
    pipeline: PipelineSection = Field(..., description="Backend processing pipeline")
