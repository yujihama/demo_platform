"""Runtime execution exceptions."""

from __future__ import annotations


class PipelineExecutionError(RuntimeError):
    """Generic runtime execution failure."""


class PipelineWait(RuntimeError):
    """Raised when a component requires user input to continue."""

    def __init__(self, component_ids: list[str]) -> None:
        super().__init__("Waiting for user input")
        self.component_ids = component_ids


