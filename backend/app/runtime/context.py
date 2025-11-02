"""Runtime context objects for workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Literal

from ..models.workflow import PipelineStep, WorkflowYaml
from ..models.runtime import SessionStateModel, StepStateModel


StepStatus = Literal["pending", "completed", "failed"]


@dataclass
class StepState:
    """Track execution status for each pipeline step."""

    status: StepStatus = "pending"
    output: Any | None = None
    error: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "output": self.output, "error": self.error}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepState":
        return cls(
            status=data.get("status", "pending"),
            output=data.get("output"),
            error=data.get("error"),
        )


@dataclass
class ExecutionContext:
    """Mutable execution context persisted in the session store."""

    session_id: str
    workflow: WorkflowYaml
    inputs: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    steps: Dict[str, StepState] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "inputs": self.inputs,
            "data": self.data,
            "steps": {key: state.to_dict() for key, state in self.steps.items()},
        }

    def to_model(self) -> SessionStateModel:
        return SessionStateModel(
            session_id=self.session_id,
            inputs=self.inputs,
            data=self.data,
            steps={key: StepStateModel(**state.to_dict()) for key, state in self.steps.items()},
        )

    @classmethod
    def from_dict(cls, workflow: WorkflowYaml, data: Dict[str, Any]) -> "ExecutionContext":
        raw_steps = data.get("steps", {})
        return cls(
            session_id=data["session_id"],
            workflow=workflow,
            inputs=data.get("inputs", {}),
            data=data.get("data", {}),
            steps={key: StepState.from_dict(value) for key, value in raw_steps.items()},
        )

    def ensure_step(self, step: PipelineStep) -> StepState:
        state = self.steps.get(step.id)
        if state is None:
            state = StepState()
            self.steps[step.id] = state
        return state

    def reset_step(self, step_id: str) -> None:
        self.steps[step_id] = StepState()

