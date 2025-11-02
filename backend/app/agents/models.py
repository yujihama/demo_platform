"""Pydantic models representing structured outputs for LLM agents."""

from __future__ import annotations

from typing import Dict, List

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RequirementItem(BaseModel):
    id: str
    category: str
    title: str
    description: str
    acceptance_criteria: List[str] = Field(default_factory=list)


class RequirementsDecompositionResult(BaseModel):
    summary: str
    primary_goal: str
    requirements: List[RequirementItem]


class AppTypeClassificationResult(BaseModel):
    app_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    recommended_template: str
    supporting_requirements: List[str] = Field(default_factory=list)


class ComponentPlacement(BaseModel):
    component_id: str
    slot: str
    props: Dict[str, Any] = Field(default_factory=dict)
    fulfills: List[str] = Field(default_factory=list)


class ComponentSelectionResult(BaseModel):
    layout_hints: List[str] = Field(default_factory=list)
    components: List[ComponentPlacement]


class DataFlowEdge(BaseModel):
    step: str
    trigger: str
    source_component: str
    target_component: str
    action: str
    description: str
    requirement_refs: List[str] = Field(default_factory=list)


class StateVariable(BaseModel):
    name: str
    type: str
    initial_value: str | None = None


class DataFlowDesignResult(BaseModel):
    state: List[StateVariable]
    flows: List[DataFlowEdge]


class ValidationIssue(BaseModel):
    code: str
    message: str
    hint: str | None = None
    level: str = Field(default="error")


class ValidationResult(BaseModel):
    success: bool
    errors: List[ValidationIssue] = Field(default_factory=list)

