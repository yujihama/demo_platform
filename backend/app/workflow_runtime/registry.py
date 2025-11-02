"""Registry for workflow runtime components."""

from __future__ import annotations

from typing import Dict

from .components.base import ComponentFactory, PipelineComponent
from backend.app.models.workflow import WorkflowYaml


class ComponentRegistry:
    """Manage mapping from component names to factories."""

    def __init__(self) -> None:
        self._factories: Dict[str, ComponentFactory] = {}

    def register(self, name: str, factory: ComponentFactory) -> None:
        self._factories[name] = factory

    def create(self, name: str, workflow: WorkflowYaml) -> PipelineComponent:
        try:
            factory = self._factories[name]
        except KeyError as exc:  # noqa: PERF203
            raise KeyError(f"Unknown component: {name}") from exc
        return factory(workflow)

    def available(self) -> Dict[str, ComponentFactory]:
        return dict(self._factories)
