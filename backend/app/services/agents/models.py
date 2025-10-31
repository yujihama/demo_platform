"""Pydantic models for Phase 2 multi-agent pipeline (skeletal).

These models intentionally keep fields minimal to unblock imports and wiring.
They can be extended in subsequent changes without breaking current callers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RequirementType(str, Enum):
    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"


class Requirement(BaseModel):
    id: str = Field(..., description="Requirement identifier")
    description: str = Field(..., description="Human readable description")
    type: RequirementType = Field(..., description="Requirement category")


class RequirementsSchema(BaseModel):
    items: List[Requirement] = Field(default_factory=list)


class AppType(str, Enum):
    TYPE_CRUD = "crud"
    TYPE_DOCUMENT_PROCESSOR = "document_processor"
    TYPE_VALIDATION = "validation"
    TYPE_ANALYTICS = "analytics"
    TYPE_CHATBOT = "chatbot"


class ClassificationResult(BaseModel):
    app_type: AppType
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    recommended_template: Optional[str] = None


class SelectedComponent(BaseModel):
    id: str
    name: str
    props: Dict[str, Any] = Field(default_factory=dict)
    requirement_ids: List[str] = Field(default_factory=list)
    order: Optional[int] = None


class ComponentSelection(BaseModel):
    components: List[SelectedComponent] = Field(default_factory=list)


class StateVariable(BaseModel):
    name: str
    type: str


class ApiCall(BaseModel):
    name: str
    endpoint: Optional[str] = None
    method: Optional[str] = None


class FlowStep(BaseModel):
    id: str
    trigger: str
    source_component: Optional[str] = None
    target_component: Optional[str] = None
    action: Optional[str] = None
    api_call: Optional[ApiCall] = None


class DataFlowDesign(BaseModel):
    steps: List[FlowStep] = Field(default_factory=list)
    state: List[StateVariable] = Field(default_factory=list)


class ValidationErrorItem(BaseModel):
    code: str
    message: str
    path: List[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    success: bool
    errors: List[ValidationErrorItem] = Field(default_factory=list)


class LlmSpecification(BaseModel):
    """Aggregated specification across agents (skeletal)."""

    requirements: RequirementsSchema
    classification: ClassificationResult
    selection: ComponentSelection
    dataflow: DataFlowDesign
