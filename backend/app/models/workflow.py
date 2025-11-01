"""Domain models representing the declarative workflow specification."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError
import yaml


class WorkflowProvider(str, Enum):
    """Supported workflow providers."""

    DIFY = "dify"
    MOCK = "mock"


class WorkflowInfo(BaseModel):
    """Metadata about the generated application."""

    name: str
    description: str
    version: str = Field(default="1.0.0")


class WorkflowEnvironment(BaseModel):
    """Environment specific override variables."""

    name: str
    variables: Dict[str, str] = Field(default_factory=dict)


class WorkflowEndpoint(BaseModel):
    """Definition of an external workflow/API that can be invoked by the engine."""

    identifier: str = Field(..., alias="id")
    display_name: str = Field(..., alias="name")
    provider: WorkflowProvider
    endpoint: str
    method: Literal["GET", "POST"] = "POST"
    headers: Dict[str, str] = Field(default_factory=dict)
    payload: Dict[str, Any] = Field(default_factory=dict)
    environments: List[WorkflowEnvironment] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class PipelineBinding(BaseModel):
    """Represents a mapping from a pipeline expression to a target name."""

    target: str
    expression: str


class CallWorkflowStep(BaseModel):
    """Pipeline step invoking an external workflow provider."""

    type: Literal["call_workflow"] = "call_workflow"
    identifier: str = Field(..., alias="id")
    name: str
    workflow: str = Field(..., description="Identifier of WorkflowEndpoint to invoke")
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    save_as: str = Field(..., description="Key under session context to store the response")
    on_error: Optional[str] = Field(
        default=None,
        description="Optional pipeline step ID to jump to when the invocation fails",
    )

    model_config = ConfigDict(populate_by_name=True)


class ForEachStep(BaseModel):
    """Executes nested steps for each element in a list expression."""

    type: Literal["for_each"] = "for_each"
    identifier: str = Field(..., alias="id")
    collection: str
    item: str
    steps: List["PipelineStep"]

    model_config = ConfigDict(populate_by_name=True)


class SetStateStep(BaseModel):
    """Assigns literal or expression value to the session context."""

    type: Literal["set_state"] = "set_state"
    identifier: str = Field(..., alias="id")
    updates: Dict[str, str]

    model_config = ConfigDict(populate_by_name=True)


PipelineStep = RootModel[CallWorkflowStep | ForEachStep | SetStateStep]


class PipelineDefinition(BaseModel):
    """Top level pipeline executing workflow steps sequentially."""

    entrypoint: str = Field("main")
    steps: Dict[str, List[PipelineStep]]


class UIComponent(BaseModel):
    """Declarative UI component definition."""

    identifier: str = Field(..., alias="id")
    type: Literal["file_upload", "button", "table", "text", "form", "container"]
    props: Dict[str, Any] = Field(default_factory=dict)
    bindings: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class UIStep(BaseModel):
    """Wizard step rendered by the generic frontend."""

    identifier: str = Field(..., alias="id")
    title: str
    description: Optional[str] = None
    layout: Literal["single_column", "two_column"] = "single_column"
    components: List[UIComponent] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class UIDefinition(BaseModel):
    """UI schema consumed by the generic frontend renderer."""

    steps: List[UIStep]


class WorkflowSpecification(BaseModel):
    """Complete declaration for an application workflow."""

    info: WorkflowInfo
    workflows: List[WorkflowEndpoint]
    pipeline: PipelineDefinition
    ui: Optional[UIDefinition] = None

    def to_yaml(self) -> str:
        """Serialise workflow to a canonical YAML string."""

        data = self.model_dump(by_alias=True)
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, yaml_text: str) -> "WorkflowSpecification":
        """Parse YAML text into a validated WorkflowSpecification."""

        try:
            payload = yaml.safe_load(yaml_text) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - handled by validator
            raise ValidationError.from_exception_data("WorkflowSpecification", []) from exc
        if not isinstance(payload, dict):
            raise ValidationError.from_exception_data("WorkflowSpecification", [])
        return cls.model_validate(payload)


PipelineStep.model_rebuild()
ForEachStep.model_rebuild()
WorkflowSpecification.model_rebuild()


__all__ = [
    "WorkflowSpecification",
    "WorkflowInfo",
    "WorkflowEndpoint",
    "WorkflowProvider",
    "PipelineDefinition",
    "PipelineStep",
    "CallWorkflowStep",
    "ForEachStep",
    "SetStateStep",
    "UIDefinition",
    "UIStep",
    "UIComponent",
]

