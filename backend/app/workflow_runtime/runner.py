"""Pipeline runner for executing workflow steps."""

from __future__ import annotations

import logging

from .context import ExecutionContext
from .exceptions import ComponentExecutionError
from .registry import ComponentRegistry
from backend.app.models.workflow import PipelineStep, WorkflowYaml

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Execute workflow pipeline steps sequentially."""

    def __init__(self, registry: ComponentRegistry) -> None:
        self._registry = registry

    def run(self, workflow: WorkflowYaml, context: ExecutionContext) -> None:
        for step in workflow.pipeline.steps:
            if not self._should_execute(step, context):
                logger.info("Skipping step %s due to condition", step.id)
                continue
            component = self._registry.create(step.component, workflow)
            params = step.params or {}
            try:
                component.execute(context, params, step_id=step.id)
                logger.info("Completed step %s", step.id)
            except ComponentExecutionError:
                raise
            except Exception as exc:  # noqa: PERF203
                logger.exception("Unhandled error in step %s", step.id)
                raise ComponentExecutionError(f"Step '{step.id}' failed: {exc}") from exc

    def _should_execute(self, step: PipelineStep, context: ExecutionContext) -> bool:
        condition = step.condition
        if not condition:
            return True
        if isinstance(condition, str) and condition.startswith("$"):
            value = context.get(condition[1:])
            return bool(value)
        return bool(condition)
