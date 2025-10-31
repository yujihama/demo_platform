"""Pydantic models for agent outputs."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RequirementType(str, Enum):
    """Types of requirements."""

    INPUT = "input"
    PROCESSING = "processing"
    OUTPUT = "output"


class AppType(str, Enum):
    """Application types."""

    TYPE_CRUD = "TYPE_CRUD"
    TYPE_DOCUMENT_PROCESSOR = "TYPE_DOCUMENT_PROCESSOR"
    TYPE_VALIDATION = "TYPE_VALIDATION"
    TYPE_ANALYTICS = "TYPE_ANALYTICS"
    TYPE_CHATBOT = "TYPE_CHATBOT"


class RequirementItem(BaseModel):
    """A single requirement item."""

    id: str = Field(..., description="Unique identifier for the requirement")
    description: str = Field(..., description="Description of the requirement")
    type: RequirementType = Field(..., description="Type of requirement")


class Agent1Output(BaseModel):
    """Output from Agent 1: Requirements Decomposition."""

    requirements: List[RequirementItem] = Field(
        ..., description="List of decomposed requirements", min_items=1
    )
    summary: str = Field(..., description="Summary of the requirements")


class Agent2Output(BaseModel):
    """Output from Agent 2: Application Type Classification."""

    app_type: AppType = Field(..., description="Classified application type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    reasoning: str = Field(..., description="Reasoning for the classification")
    template_structure: Dict[str, Any] = Field(default_factory=dict, description="Recommended template structure")


class ComponentPosition(BaseModel):
    """Position information for a component."""

    step: int = Field(..., description="Step number in the wizard", ge=1)
    section: str = Field(..., description="Section name within the step")


class ComponentProps(BaseModel):
    """Properties for a component."""

    label: Optional[str] = None
    placeholder: Optional[str] = None
    required: Optional[bool] = None
    options: Optional[List[str]] = None
    type: Optional[str] = None
    additional_props: Dict[str, Any] = Field(default_factory=dict)


class SelectedComponent(BaseModel):
    """A selected UI component."""

    component_id: str = Field(..., description="ID from the UI parts catalog")
    position: ComponentPosition = Field(..., description="Position in the wizard")
    props: ComponentProps = Field(..., description="Component properties")
    requirement_ids: List[str] = Field(..., description="IDs of requirements this component fulfills", min_items=1)


class Agent3Output(BaseModel):
    """Output from Agent 3: Component Selection."""

    components: List[SelectedComponent] = Field(..., description="Selected UI components", min_items=1)
    reasoning: str = Field(..., description="Reasoning for component selection")


class DataFlowStep(BaseModel):
    """A step in the data flow."""

    step_id: str = Field(..., description="Unique identifier for the step")
    trigger: str = Field(..., description="What triggers this step (e.g., 'form_submit', 'button_click')")
    source_component: Optional[str] = Field(None, description="Source component ID")
    target_component: Optional[str] = Field(None, description="Target component ID")
    api_call: Optional[Dict[str, Any]] = Field(None, description="API call definition")
    state_variables: List[str] = Field(default_factory=list, description="State variables affected")
    type_definitions: Dict[str, str] = Field(default_factory=dict, description="Type definitions for variables")


class Agent4Output(BaseModel):
    """Output from Agent 4: Data Flow Design."""

    data_flow: List[DataFlowStep] = Field(..., description="Data flow steps", min_items=1)
    global_state: Dict[str, str] = Field(default_factory=dict, description="Global state variable types")


class ValidationError(BaseModel):
    """A validation error."""

    rule: str = Field(..., description="Validation rule that failed")
    message: str = Field(..., description="Error message")
    component_id: Optional[str] = Field(None, description="Component ID if applicable")


class ValidatorOutput(BaseModel):
    """Output from Validator Agent."""

    is_valid: bool = Field(..., description="Whether the specification is valid")
    errors: List[ValidationError] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of warnings")
