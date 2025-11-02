"""Custom exceptions for the workflow runtime."""


class WorkflowRuntimeError(Exception):
    """Base class for workflow runtime errors."""


class WorkflowNotFoundError(WorkflowRuntimeError):
    """Raised when the workflow definition cannot be located."""


class SessionNotFoundError(WorkflowRuntimeError):
    """Raised when attempting to access a missing session."""


class ComponentExecutionError(WorkflowRuntimeError):
    """Raised when a component fails during execution."""


class InvalidComponentConfigError(WorkflowRuntimeError):
    """Raised when component parameters are invalid."""


class ProviderConfigurationError(WorkflowRuntimeError):
    """Raised when workflow provider configuration is invalid."""
