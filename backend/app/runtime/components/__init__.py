"""Component registry for workflow runtime."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TYPE_CHECKING

from ..context import ExecutionContext, StepState

if TYPE_CHECKING:  # pragma: no cover - circular import guard
    from ..engine import WorkflowEngine

ComponentHandler = Callable[[ExecutionContext, dict[str, Any], "WorkflowEngine"], Awaitable[StepState]]
