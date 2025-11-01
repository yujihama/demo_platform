"""Pydantic models representing the declarative workflow document."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, validator


WorkflowProviderType = Literal["dify", "mock", "http"]


class WorkflowInfo(BaseModel):
    """Top level metadata for the generated application."""

    name: str = Field(..., description="?????????????????")
    summary: Optional[str] = Field(None, description="???????????")
    version: str = Field("1.0.0", description="??????????????")


class WorkflowProvider(BaseModel):
    """External workflow provider definition (e.g. Dify)."""

    id: str = Field(..., description="?????????")
    provider: WorkflowProviderType = Field(..., description="????????")
    endpoint: str | HttpUrl = Field(..., description="????????????")
    method: Literal["GET", "POST"] = Field("POST", description="HTTP????")
    headers: Dict[str, str] = Field(default_factory=dict, description="??HTTP????")
    inputs: Dict[str, str] = Field(default_factory=dict, description="??????????????")
    outputs: Dict[str, str] = Field(default_factory=dict, description="?????????")

    @validator("id")
    def _validate_id(cls, value: str) -> str:
        if not value:
            raise ValueError("provider id ?????")
        return value


class WorkflowPipelineStep(BaseModel):
    """Single executable step in the pipeline section."""

    id: str = Field(..., description="???????")
    type: Literal[
        "call_workflow",
        "transform",
        "for_each",
        "set_state",
        "branch",
    ] = Field(..., description="??????")
    title: Optional[str] = Field(None, description="????????")
    with_: Dict[str, Any] = Field(default_factory=dict, alias="with", description="???????")
    on_success: List[str] = Field(default_factory=list, description="????????????ID??")
    on_error: List[str] = Field(default_factory=list, description="?????????????ID??")

    class Config:
        populate_by_name = True

    @validator("id")
    def _validate_step_id(cls, value: str) -> str:
        if not value:
            raise ValueError("pipeline step id ?????")
        return value


class WorkflowUIComponent(BaseModel):
    """Declarative UI component definition."""

    id: str = Field(..., description="UI???????ID")
    type: Literal[
        "file_upload",
        "button",
        "text",
        "table",
        "form",
        "markdown",
        "progress",
    ] = Field(..., description="?????????")
    label: Optional[str] = Field(None, description="UI???")
    props: Dict[str, Any] = Field(default_factory=dict, description="????????")
    bindings: Dict[str, str] = Field(default_factory=dict, description="????????????")

    @validator("id")
    def _validate_component_id(cls, value: str) -> str:
        if not value:
            raise ValueError("UI component id ?????")
        return value


class WorkflowUIStep(BaseModel):
    """Single step within the wizard UI."""

    id: str = Field(..., description="UI????ID")
    title: str = Field(..., description="????????")
    description: Optional[str] = Field(None, description="??????")
    components: List[WorkflowUIComponent] = Field(default_factory=list, description="???????????????")


class WorkflowUI(BaseModel):
    """Top level UI definition derived from the workflow document."""

    layout: Literal["wizard", "single-page"] = Field("wizard", description="???????")
    steps: List[WorkflowUIStep] = Field(default_factory=list, description="???????????")


class WorkflowDocument(BaseModel):
    """Aggregate document representing workflow.yaml."""

    version: str = Field("1", description="?????????")
    info: WorkflowInfo
    workflows: List[WorkflowProvider] = Field(default_factory=list, description="????????????")
    pipeline: List[WorkflowPipelineStep] = Field(default_factory=list, description="??????????")
    ui: WorkflowUI

    @validator("workflows")
    def _ensure_provider_ids_unique(cls, providers: List[WorkflowProvider]) -> List[WorkflowProvider]:
        seen = set()
        for provider in providers:
            if provider.id in seen:
                raise ValueError(f"??????ID '{provider.id}' ????????")
            seen.add(provider.id)
        return providers

    @validator("pipeline")
    def _ensure_pipeline_ids_unique(cls, steps: List[WorkflowPipelineStep]) -> List[WorkflowPipelineStep]:
        seen = set()
        for step in steps:
            if step.id in seen:
                raise ValueError(f"??????????ID '{step.id}' ????????")
            seen.add(step.id)
        return steps

