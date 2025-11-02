"""Component base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from ..context import ExecutionContext
from backend.app.models.workflow import WorkflowYaml


class PipelineComponent(ABC):
    """Base interface for pipeline components."""

    @abstractmethod
    def execute(self, context: ExecutionContext, params: dict[str, Any], *, step_id: str) -> None:
        """Execute the component with given parameters."""


ComponentFactory = Callable[[WorkflowYaml], PipelineComponent]
