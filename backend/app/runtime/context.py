"""Execution context shared across pipeline components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from .models import ComponentState, SessionState
from .state import RuntimeStateStore
from ...models.workflow import WorkflowYaml


@dataclass
class ExecutionContext:
    """Holds runtime state for pipeline execution."""

    workflow: WorkflowYaml
    session: SessionState
    store: RuntimeStateStore
    data: Dict[str, Any] = field(default_factory=dict)

    def get_component_value(self, component_id: str) -> ComponentState | None:
        return self.session.component_state.get(component_id)

    def set_component_value(self, component_id: str, value: Any, status: str = "ready") -> None:
        state = self.session.component_state.get(component_id)
        if state is None:
            state = ComponentState()
        state.value = value
        state.status = status
        self.session.component_state[component_id] = state

    def set_context_value(self, key: str, value: Any) -> None:
        self.session.context[key] = value

    def get_context_value(self, key: str, default: Any = None) -> Any:
        return self.session.context.get(key, default)

    def workflow_provider(self, workflow_name: str) -> str:
        provider = self.workflow.workflows[workflow_name].provider
        return provider

    def workflow_endpoint(self, workflow_name: str) -> str:
        return self.workflow.workflows[workflow_name].endpoint


