"""Workflow execution engine."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict

import httpx
import yaml
from fastapi import UploadFile

from ..models.workflow import PipelineStep, WorkflowYaml
from .components.call_workflow import call_workflow
from .components.file_uploader import ensure_file_present, handle_file_upload
from .components.for_each import for_each
from .context import ExecutionContext, StepState
from .errors import MissingInputError, UnknownComponentError, WorkflowRuntimeError
from .session_store import BaseSessionStore, InMemorySessionStore, RedisSessionStore, build_session_store


class WorkflowEngine:
    """Coordinates workflow execution and session state."""

    def __init__(
        self,
        workflow_path: str | Path | None = None,
        session_store: BaseSessionStore | None = None,
        http_timeout: float = 30.0,
    ) -> None:
        self._workflow_path = Path(workflow_path or os.environ.get("WORKFLOW_FILE", "workflow.yaml"))
        if not self._workflow_path.exists():
            raise FileNotFoundError(f"workflow.yaml not found at {self._workflow_path}")

        self._workflow = self._load_workflow(self._workflow_path)
        self._session_store = session_store or build_session_store()
        self._http_timeout = http_timeout

        self._component_handlers: Dict[
            str,
            Callable[[ExecutionContext, dict[str, Any], "WorkflowEngine"], Awaitable[StepState]],
        ] = {
            "call_workflow": call_workflow,
            "for_each": for_each,
        }

    @property
    def workflow(self) -> WorkflowYaml:
        return self._workflow

    @property
    def http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self._http_timeout)

    async def ensure_ready(self) -> None:
        if isinstance(self._session_store, RedisSessionStore):
            healthy = await self._session_store.ping()
            if not healthy:
                self._session_store = InMemorySessionStore()

    async def create_session(self) -> ExecutionContext:
        session_id = uuid.uuid4().hex
        context = ExecutionContext(session_id=session_id, workflow=self._workflow)
        for step in self._workflow.pipeline.steps:
            context.ensure_step(step)
        await self._session_store.create(session_id, context.to_dict())
        return context

    async def get_session(self, session_id: str) -> ExecutionContext | None:
        payload = await self._session_store.get(session_id)
        if payload is None:
            return None
        return ExecutionContext.from_dict(self._workflow, payload)

    async def save_session(self, context: ExecutionContext) -> None:
        await self._session_store.update(context.session_id, context.to_dict())

    async def delete_session(self, session_id: str) -> None:
        await self._session_store.delete(session_id)

    async def store_file_input(self, session_id: str, step_id: str, file: UploadFile) -> ExecutionContext:
        context = await self._require_session(session_id)
        step = self._require_step(step_id)
        if step.component != "file_uploader":
            raise WorkflowRuntimeError("File uploads can only target file_uploader steps")

        state = await handle_file_upload(context, step.params, file)
        context.steps[step.id] = state
        index = self._workflow.pipeline.steps.index(step)
        for later_step in self._workflow.pipeline.steps[index + 1 :]:
            context.reset_step(later_step.id)
        await self.save_session(context)
        return context

    async def execute(self, session_id: str) -> ExecutionContext:
        context = await self._require_session(session_id)
        for step in self._workflow.pipeline.steps:
            state = context.ensure_step(step)
            if state.status == "completed":
                continue

            try:
                result = await self._execute_step(context, step)
            except WorkflowRuntimeError as exc:
                if isinstance(exc, MissingInputError):
                    state.status = "pending"
                    state.error = str(exc)
                else:
                    state.status = "failed"
                    state.error = str(exc)
                await self.save_session(context)
                raise
            else:
                context.steps[step.id] = result

        await self.save_session(context)
        return context

    # ------------------------------------------------------------------
    async def _execute_step(self, context: ExecutionContext, step: PipelineStep) -> StepState:
        if step.component == "file_uploader":
            ensure_file_present(context, step.params)
            metadata = context.inputs.get(step.params.get("input_key", ""), {})
            return StepState(status="completed", output=metadata)

        handler = self._component_handlers.get(step.component)
        if handler is None:
            raise UnknownComponentError(f"Unknown pipeline component: {step.component}")

        return await handler(context, step.params, self)

    async def _require_session(self, session_id: str) -> ExecutionContext:
        context = await self.get_session(session_id)
        if context is None:
            raise WorkflowRuntimeError(f"Session '{session_id}' not found")
        return context

    def _require_step(self, step_id: str) -> PipelineStep:
        matches = [step for step in self._workflow.pipeline.steps if step.id == step_id]
        if not matches:
            raise WorkflowRuntimeError(f"Unknown pipeline step '{step_id}'")
        return matches[0]

    @staticmethod
    def _load_workflow(path: Path) -> WorkflowYaml:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        return WorkflowYaml(**raw)


_ENGINE_INSTANCE: WorkflowEngine | None = None


def build_engine() -> WorkflowEngine:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        _ENGINE_INSTANCE = WorkflowEngine()
    return _ENGINE_INSTANCE
