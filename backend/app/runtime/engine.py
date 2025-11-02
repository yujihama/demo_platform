"""Workflow runtime engine that executes workflow.yaml pipeline definitions."""

from __future__ import annotations

import inspect
import logging
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

import httpx
import yaml
from redis.asyncio import Redis

from ..config import config_manager
from ..models.workflow import PipelineStep, WorkflowYaml
from .components import (
    ComponentHandler,
    ExecutionContext,
    ExecutionResult,
    create_call_workflow_component,
    file_uploader,
    for_each,
)
from .models import WorkflowSession, WorkflowSessionPublicState
from .state import InMemoryStateStore, RedisStateStore, StateStoreProtocol
from .utils import deep_merge, render_template, truthy

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Execute workflow pipelines defined in workflow.yaml."""

    def __init__(
        self,
        workflow: WorkflowYaml,
        state_store: StateStoreProtocol,
        session_ttl: int,
        call_workflow_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
    ) -> None:
        self._workflow = workflow
        self._state_store = state_store
        self._session_ttl = session_ttl
        self._components: Dict[str, ComponentHandler] = {
            "file_uploader": file_uploader,
            "for_each": for_each,
            "call_workflow": create_call_workflow_component(call_workflow_factory),
        }
        self._step_by_id: Dict[str, PipelineStep] = {
            step.id: step for step in self._workflow.pipeline.steps
        }
        self._step_order = [step.id for step in self._workflow.pipeline.steps]
        self._step_index = {step_id: idx for idx, step_id in enumerate(self._step_order)}
        self._ui_order = [step.id for step in (self._workflow.ui.steps if self._workflow.ui else [])]
        self._ui_index = {step_id: idx for idx, step_id in enumerate(self._ui_order)}
        self._call_workflow_component = self._components["call_workflow"]

    # ------------------------------------------------------------------
    @property
    def workflow(self) -> WorkflowYaml:
        return self._workflow

    # ------------------------------------------------------------------
    async def create_session(self) -> WorkflowSessionPublicState:
        session_id = str(uuid4())
        workflow_id = self._workflow.info.name
        session = WorkflowSession(session_id=session_id, workflow_id=workflow_id)
        for step_id in self._step_order:
            session.step_status[step_id] = "pending"
        if self._ui_order:
            session.active_ui_step = self._ui_order[0]
        await self._state_store.create(session, self._session_ttl)
        logger.info("Created workflow session %s", session_id)
        return session.to_public_state()

    # ------------------------------------------------------------------
    async def get_session(self, session_id: str) -> Optional[WorkflowSessionPublicState]:
        session = await self._state_store.load(session_id)
        if session is None:
            return None
        return session.to_public_state()

    # ------------------------------------------------------------------
    async def submit_step(
        self,
        session_id: str,
        step_id: str,
        payload: Dict[str, Any],
        file: Any = None,
    ) -> WorkflowSessionPublicState:
        session = await self._state_store.load(session_id)
        if session is None:
            raise ValueError("指定されたセッションは存在しません。")

        expected_step = self._next_user_step(session.pipeline_index)
        if expected_step and expected_step.id != step_id:
            raise ValueError("想定されていないステップが実行されました。")

        step = self._step_by_id.get(step_id)
        if step is None:
            raise ValueError(f"定義されていないステップ {step_id} が指定されました。")

        handler = self._components.get(step.component)
        if handler is None:
            raise ValueError(f"未対応のコンポーネント {step.component} が指定されました。")

        session.status = "processing"
        session.step_status[step_id] = "running"
        session.last_error = None
        session.touch()

        try:
            await self._execute_step(session, step, handler, payload, file)
            await self._execute_autonomous_steps(session)
            self._update_session_status(session)
        except Exception as exc:  # noqa: BLE001 - propagate meaningful error
            logger.exception("Failed to execute step %s for session %s", step_id, session_id)
            session.step_status[step_id] = "error"
            session.status = "awaiting_input"
            session.last_error = str(exc)
            session.touch()
            await self._state_store.save(session, self._session_ttl)
            raise

        session.touch()
        await self._state_store.save(session, self._session_ttl)
        return session.to_public_state()

    # ------------------------------------------------------------------
    async def _execute_step(
        self,
        session: WorkflowSession,
        step: PipelineStep,
        handler: ComponentHandler,
        payload: Dict[str, Any],
        file: Any = None,
    ) -> None:
        if step.condition:
            condition_value = render_template(step.condition, self.build_template_context(session))
            if not truthy(condition_value):
                session.step_status[step.id] = "completed"
                session.pipeline_index = self._step_index[step.id]
                return

        if session.step_status.get(step.id) != "running":
            session.step_status[step.id] = "running"

        exec_context = ExecutionContext(engine=self, session=session, step=step)
        result = await handler.execute(exec_context, payload, file)
        if result is None:
            result = ExecutionResult()

        self._apply_result(session, step, handler, result)

    # ------------------------------------------------------------------
    async def _execute_autonomous_steps(self, session: WorkflowSession) -> None:
        idx = session.pipeline_index
        while True:
            next_idx = idx + 1
            if next_idx >= len(self._step_order):
                break
            step_id = self._step_order[next_idx]
            step = self._step_by_id[step_id]
            handler = self._components.get(step.component)
            if handler is None:
                raise ValueError(f"未対応のコンポーネント {step.component} が指定されました。")
            if handler.requires_user_input:
                break
            await self._execute_step(session, step, handler, payload={}, file=None)
            idx = session.pipeline_index

    # ------------------------------------------------------------------
    def _apply_result(
        self,
        session: WorkflowSession,
        step: PipelineStep,
        handler: ComponentHandler,
        result: ExecutionResult,
    ) -> None:
        if result.public:
            session.context.public = deep_merge(session.context.public, result.public)
        if result.private:
            session.context.private = deep_merge(session.context.private, result.private)
        if result.step_output:
            session.step_outputs[step.id] = result.step_output
        session.step_status[step.id] = "completed"
        session.pipeline_index = self._step_index[step.id]
        self._update_ui_state(session, step, handler)

    # ------------------------------------------------------------------
    def _update_ui_state(
        self,
        session: WorkflowSession,
        step: PipelineStep,
        handler: ComponentHandler,
    ) -> None:
        ui_step = step.params.get("ui_step")
        activate = step.params.get("activate_ui_step")

        if handler.requires_user_input and ui_step:
            if ui_step not in session.completed_ui_steps:
                session.completed_ui_steps.append(ui_step)
            next_ui = activate or self._next_ui_step(ui_step)
            session.active_ui_step = next_ui or ui_step
        else:
            if activate:
                session.active_ui_step = activate
            elif ui_step:
                session.active_ui_step = ui_step

    # ------------------------------------------------------------------
    def _update_session_status(self, session: WorkflowSession) -> None:
        if session.last_error:
            session.status = "awaiting_input"
            return
        next_step = self._next_user_step(session.pipeline_index)
        if next_step is None:
            session.status = "completed"
        else:
            session.status = "awaiting_input"
            ui_step = next_step.params.get("ui_step")
            if ui_step:
                session.active_ui_step = ui_step

    # ------------------------------------------------------------------
    def _next_user_step(self, index: int) -> Optional[PipelineStep]:
        for next_idx in range(index + 1, len(self._step_order)):
            candidate = self._step_by_id[self._step_order[next_idx]]
            handler = self._components.get(candidate.component)
            if handler and handler.requires_user_input:
                return candidate
        return None

    # ------------------------------------------------------------------
    def _next_ui_step(self, ui_step_id: str) -> Optional[str]:
        idx = self._ui_index.get(ui_step_id)
        if idx is None:
            return None
        next_idx = idx + 1
        if next_idx >= len(self._ui_order):
            return None
        return self._ui_order[next_idx]

    # ------------------------------------------------------------------
    def build_template_context(self, session: WorkflowSession) -> Dict[str, Any]:
        merged = session.context.merged()
        context_data: Dict[str, Any] = {
            **merged,
            "context": session.context.public,
            "public": session.context.public,
            "private": session.context.private,
            "steps": session.step_outputs,
        }
        return context_data

    # ------------------------------------------------------------------
    async def shutdown(self) -> None:
        call_workflow = getattr(self._call_workflow_component, "close", None)
        if callable(call_workflow):
            await call_workflow()  # type: ignore[arg-type]


_engine_instance: Optional[WorkflowEngine] = None
_redis_client: Optional[Redis] = None


def load_workflow(path: Path) -> WorkflowYaml:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return WorkflowYaml.model_validate(data)


def get_runtime_engine() -> WorkflowEngine:
    global _engine_instance, _redis_client
    if _engine_instance is not None:
        return _engine_instance

    cfg = config_manager.features.runtime
    workflow = load_workflow(cfg.workflow_path)

    redis_client: Optional[Redis] = None
    state_store: StateStoreProtocol
    try:
        redis_client = Redis.from_url(cfg.redis_url, decode_responses=True)
        state_store = RedisStateStore(redis_client)
        logger.info("Workflow runtime will use Redis at %s", cfg.redis_url)
    except Exception:  # noqa: BLE001 - fallback handling
        logger.exception("Redis 初期化に失敗したため、インメモリストアにフォールバックします。")
        state_store = InMemoryStateStore()

    _engine_instance = WorkflowEngine(
        workflow=workflow,
        state_store=state_store,
        session_ttl=cfg.session_ttl_seconds,
    )
    _redis_client = redis_client
    return _engine_instance


async def shutdown_runtime_engine() -> None:
    global _engine_instance, _redis_client
    if _engine_instance is not None:
        await _engine_instance.shutdown()
        _engine_instance = None
    if _redis_client is not None:
        close_result = _redis_client.close()
        if inspect.isawaitable(close_result):
            await close_result
        _redis_client = None
