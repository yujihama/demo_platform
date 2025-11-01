"""Structured LLM output models for declarative workflow generation."""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field


class AnalystRequirement(BaseModel):
    """Individual functional requirement extracted by the Analyst agent."""

    id: str
    title: str
    detail: str
    category: Literal["input", "process", "output", "validation"]
    acceptance_criteria: List[str] = Field(default_factory=list)


class AnalystResult(BaseModel):
    """Analyst agent structured summary of the user need."""

    primary_goal: str
    domain_context: str
    requirements: List[AnalystRequirement] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    sample_inputs: List[str] = Field(default_factory=list)


class WorkflowReferencePlan(BaseModel):
    """Reference to external workflow provider planned by the Architect agent."""

    id: str
    provider_type: Literal["dify", "mock", "http"]
    endpoint: str
    description: str


class UIStepPlan(BaseModel):
    """Single UI step blueprint produced by the Architect agent."""

    id: str
    title: str
    description: str
    components: List[str] = Field(default_factory=list)
    success_transition: str | None = Field(default=None, description="Successful transition target step id")


class PipelineStepPlan(BaseModel):
    """Pipeline blueprint entry prior to YAML generation."""

    id: str
    type: Literal["call_workflow", "transform", "for_each", "set_state", "branch"]
    description: str
    uses_provider: str | None = None
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)


class ArchitecturePlan(BaseModel):
    """Combined UI/Pipeline plan from the Architect agent."""

    title: str
    summary: str
    ui_steps: List[UIStepPlan] = Field(default_factory=list)
    pipeline: List[PipelineStepPlan] = Field(default_factory=list)
    workflows: List[WorkflowReferencePlan] = Field(default_factory=list)


class WorkflowDraft(BaseModel):
    """YAML draft output produced by the Specialist agent."""

    workflow_yaml: str = Field(..., description="YAML??")
    notes: List[str] = Field(default_factory=list)


class ValidatorFeedback(BaseModel):
    """Validator outcome summarised for the self-healing loop."""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

