"""Component registry initialisation."""

from __future__ import annotations

from .base import ComponentRegistry
from .call_workflow import CallWorkflowComponent
from .file_uploader import FileUploaderComponent
from .for_each import ForEachComponent


def build_component_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register("call_workflow", CallWorkflowComponent())
    registry.register("file_uploader", FileUploaderComponent())
    registry.register("for_each", ForEachComponent())
    return registry


__all__ = ["build_component_registry", "ComponentRegistry"]

