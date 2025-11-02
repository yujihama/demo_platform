"""Base classes for workflow runtime components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from starlette.datastructures import UploadFile

from ...models.workflow import PipelineStep
from ..models import WorkflowSession

if False:  # pragma: no cover - for type checking only
    from ..engine import WorkflowEngine


@dataclass
class ExecutionContext:
    """Context passed to component handlers during execution."""

    engine: "WorkflowEngine"
    session: WorkflowSession
    step: PipelineStep


@dataclass
class ExecutionResult:
    """Result produced by a component handler."""

    public: Dict[str, Any] = field(default_factory=dict)
    private: Dict[str, Any] = field(default_factory=dict)
    step_output: Dict[str, Any] = field(default_factory=dict)
    next_step: Optional[str] = None


class ComponentHandler:
    """Base component handler."""

    requires_user_input: bool = False

    async def execute(
        self,
        context: ExecutionContext,
        payload: Dict[str, Any],
        file: Optional[UploadFile] = None,
    ) -> ExecutionResult:  # pragma: no cover - interface
        raise NotImplementedError
