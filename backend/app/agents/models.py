"""Structured outputs for the declarative workflow multi-agent pipeline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..models.workflow import WorkflowProvider


class AnalystInsight(BaseModel):
    """Summary produced by the analyst agent."""

    app_name: str
    summary: str
    user_persona: str
    primary_actions: List[str]
    data_entities: List[str]
    success_metrics: List[str]
    assumptions: List[str] = Field(default_factory=list)


class WorkflowAdapterConfig(BaseModel):
    """Descriptor for external workflow endpoints."""

    identifier: str = Field(..., alias="id")
    name: str
    provider: WorkflowProvider
    endpoint: str
    method: str = "POST"
    description: str


class PipelineStepPlan(BaseModel):
    """Intermediate pipeline step plan before conversion to runtime spec."""

    identifier: str = Field(..., alias="id")
    type: str
    description: str
    workflow: Optional[str] = None
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    save_as: Optional[str] = None
    updates: Dict[str, str] = Field(default_factory=dict)
    steps: List["PipelineStepPlan"] = Field(default_factory=list)


class UIComponentPlan(BaseModel):
    identifier: str = Field(..., alias="id")
    type: str
    props: Dict[str, Any] = Field(default_factory=dict)
    bindings: Dict[str, str] = Field(default_factory=dict)


class UIStepPlan(BaseModel):
    identifier: str = Field(..., alias="id")
    title: str
    description: Optional[str] = None
    layout: str = "single_column"
    components: List[UIComponentPlan] = Field(default_factory=list)


class ArchitectBlueprint(BaseModel):
    """Output of the architect agent describing workflows, pipeline, and UI."""

    workflows: List[WorkflowAdapterConfig]
    pipeline: List[PipelineStepPlan]
    ui: List[UIStepPlan]


class ValidationIssue(BaseModel):
    code: str
    message: str
    hint: Optional[str] = None
    level: str = "error"


class ValidatorReport(BaseModel):
    success: bool
    issues: List[ValidationIssue] = Field(default_factory=list)
    corrected_yaml: Optional[str] = None


PipelineStepPlan.model_rebuild()


__all__ = [
    "AnalystInsight",
    "ArchitectBlueprint",
    "WorkflowAdapterConfig",
    "PipelineStepPlan",
    "UIComponentPlan",
    "UIStepPlan",
    "ValidationIssue",
    "ValidatorReport",
]

