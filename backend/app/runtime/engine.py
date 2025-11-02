"""Runtime execution engine implementation."""

from __future__ import annotations

import logging
from uuid import uuid4

import yaml

from ..models.workflow import WorkflowYaml
from .components.base import ComponentRegistry
from .context import ExecutionContext
from .exceptions import PipelineExecutionError, PipelineWait
from .models import SessionState
from .state import RuntimeStateStore

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """Main orchestrator for executing workflow pipelines."""

    def __init__(
        self,
        workflow: WorkflowYaml,
        store: RuntimeStateStore,
        registry: ComponentRegistry,
    ) -> None:
        self._workflow = workflow
        self._store = store
        self._registry = registry

    @property
    def workflow(self) -> WorkflowYaml:
        return self._workflow

    async def create_session(self) -> SessionState:
        session = SessionState(
            session_id=str(uuid4()),
            active_step_id=self._workflow.ui.steps[0].id if self._workflow.ui and self._workflow.ui.steps else None,
        )
        await self._store.create_session(session)
        return session

    async def load_session(self, session_id: str) -> SessionState | None:
        return await self._store.get_session(session_id)

    async def save_session(self, session: SessionState) -> SessionState:
        return await self._store.save_session(session)

    async def advance(self, session: SessionState) -> SessionState:
        context = ExecutionContext(self._workflow, session, self._store, data=dict(session.context))
        session.status = "running"
        session.waiting_for = []

        steps = self._workflow.pipeline.steps
        while session.next_step_index < len(steps):
            step = steps[session.next_step_index]
            component = self._registry.get(step.component)
            try:
                await component.run(step, context)
            except PipelineWait as wait:
                session.status = "waiting"
                session.waiting_for = wait.component_ids
                logger.info("Pipeline waiting for input", extra={"session": session.session_id, "components": wait.component_ids})
                break
            except Exception as exc:  # noqa: BLE001 - we want to wrap generic exceptions
                session.status = "failed"
                session.last_error = str(exc)
                logger.exception("Pipeline execution failed", extra={"session": session.session_id, "step": step.id})
                raise PipelineExecutionError(str(exc)) from exc
            else:
                session.next_step_index += 1
                session.context.update(context.session.context)

        if session.next_step_index >= len(steps) and session.status != "failed":
            session.status = "completed"
            session.waiting_for = []
            if self._workflow.ui and self._workflow.ui.steps:
                session.active_step_id = self._workflow.ui.steps[-1].id

        await self._store.save_session(session)
        return session

    def reload_workflow(self, payload: str) -> None:
        data = yaml.safe_load(payload)
        self._workflow = WorkflowYaml(**data)


