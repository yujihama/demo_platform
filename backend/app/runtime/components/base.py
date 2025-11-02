"""Base classes for pipeline components."""

from __future__ import annotations

from typing import Any, Dict, Protocol

from ..context import ExecutionContext
from ..exceptions import PipelineExecutionError, PipelineWait
from ...models.workflow import PipelineStep


class PipelineComponent(Protocol):
    """Pipeline component interface."""

    async def run(self, step: PipelineStep, context: ExecutionContext) -> None:  # pragma: no cover - protocol
        ...


class ComponentRegistry:
    """Registry mapping component names to implementations."""

    def __init__(self) -> None:
        self._components: Dict[str, PipelineComponent] = {}

    def register(self, name: str, component: PipelineComponent) -> None:
        self._components[name] = component

    def get(self, name: str) -> PipelineComponent:
        try:
            return self._components[name]
        except KeyError as exc:
            raise PipelineExecutionError(f"Unknown component: {name}") from exc


