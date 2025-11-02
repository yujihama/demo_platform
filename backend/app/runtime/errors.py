"""Custom exceptions for the workflow runtime."""

from __future__ import annotations


class WorkflowRuntimeError(Exception):
    """Base exception for workflow runtime failures."""


class MissingInputError(WorkflowRuntimeError):
    """Raised when a required user input has not been provided."""


class ComponentExecutionError(WorkflowRuntimeError):
    """Raised when a pipeline component fails to execute."""


class UnknownComponentError(WorkflowRuntimeError):
    """Raised when the pipeline references an unknown component."""
