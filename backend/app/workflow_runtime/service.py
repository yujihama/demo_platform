"""High level orchestration for executing workflow.yaml."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

import httpx
import yaml

from backend.app.models.workflow import WorkflowYaml
from .context import ExecutionContext
from .exceptions import SessionNotFoundError, WorkflowNotFoundError
from .registry import ComponentRegistry
from .runner import PipelineRunner
from .session import WorkflowSession
from .storage import SessionStore
from .components.call_workflow import CallWorkflowComponent
from .components.file_uploader import FileUploaderComponent
from .components.for_each import ForEachComponent

logger = logging.getLogger(__name__)


class WorkflowRuntimeService:
    """Service that coordinates workflow loading, session management, and execution."""

    def __init__(
        self,
        workflow_path: Path,
        session_store: SessionStore,
        *,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._workflow_path = workflow_path
        self._session_store = session_store
        self._http_client = http_client or httpx.Client()
        self._registry = ComponentRegistry()
        self._runner = PipelineRunner(self._registry)
        self._workflow_cache: Optional[WorkflowYaml] = None
        self._register_components()

    # ------------------------------------------------------------------
    def _register_components(self) -> None:
        self._registry.register(
            "call_workflow",
            lambda workflow: CallWorkflowComponent(workflow, self._http_client),
        )
        self._registry.register("file_uploader", lambda workflow: FileUploaderComponent(workflow))
        self._registry.register("for_each", lambda workflow: ForEachComponent(workflow))

    # ------------------------------------------------------------------
    def load_workflow(self, force: bool = False) -> WorkflowYaml:
        if self._workflow_cache is not None and not force:
            return self._workflow_cache
        if not self._workflow_path.exists():
            raise WorkflowNotFoundError(f"workflow.yaml not found at {self._workflow_path}")
        with self._workflow_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        workflow = WorkflowYaml.model_validate(data)
        self._workflow_cache = workflow
        return workflow

    # ------------------------------------------------------------------
    def create_session(self) -> WorkflowSession:
        workflow = self.load_workflow()
        session = WorkflowSession(session_id=str(uuid4()))
        session.data = {"inputs": {}, "steps": {}, "workflow_info": workflow.info.model_dump()}
        session.view = {"steps": {}, "info": workflow.info.model_dump()}
        self._session_store.save(session)
        logger.info("Created workflow session %s", session.session_id)
        return session

    # ------------------------------------------------------------------
    def get_session(self, session_id: str) -> WorkflowSession:
        session = self._session_store.load(session_id)
        if session is None:
            raise SessionNotFoundError(f"Session {session_id} not found")
        return session

    # ------------------------------------------------------------------
    def execute_session(
        self,
        session_id: str,
        inputs: Dict[str, Any] | None = None,
        *,
        step_id: Optional[str] = None,
    ) -> WorkflowSession:
        workflow = self.load_workflow()
        session = self.get_session(session_id)

        session.mark_running(step_id)
        self._session_store.save(session)

        context = ExecutionContext(dict(session.data), dict(session.view))
        if inputs:
            merged_inputs = context.get("inputs", {})
            if not isinstance(merged_inputs, dict):
                merged_inputs = {}
            merged_inputs.update(inputs)
            context.set("inputs", merged_inputs)

        try:
            self._runner.run(workflow, context)
        except Exception as exc:  # noqa: PERF203
            session.mark_failed(str(exc))
            self._session_store.save(session)
            raise

        data_snapshot, view_snapshot = context.snapshot()
        session.data = data_snapshot
        session.view = view_snapshot
        session.mark_completed()
        self._session_store.save(session)
        logger.info("Session %s completed", session.session_id)
        return session

    # ------------------------------------------------------------------
    def sanitize_view(self, session: WorkflowSession) -> Dict[str, Any]:
        view = dict(session.view)
        return view

    # ------------------------------------------------------------------
    def sanitize_context(self, session: WorkflowSession) -> Dict[str, Any]:
        data = dict(session.data)
        if "inputs" in data:
            sanitized_inputs = {}
            for key, value in data["inputs"].items():
                if isinstance(value, dict):
                    sanitized_inputs[key] = {
                        k: value.get(k)
                        for k in ("name", "content_type", "size")
                        if k in value
                    }
                else:
                    sanitized_inputs[key] = value
            data["inputs"] = sanitized_inputs
        return data

    # ------------------------------------------------------------------
    def close(self) -> None:
        self._http_client.close()
