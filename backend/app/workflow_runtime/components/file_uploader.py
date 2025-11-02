"""Component that stores uploaded file metadata in the execution context."""

from __future__ import annotations

import base64
from typing import Any

from ..context import ExecutionContext
from ..exceptions import ComponentExecutionError, InvalidComponentConfigError
from .base import PipelineComponent
from ...models.workflow import WorkflowYaml


class FileUploaderComponent(PipelineComponent):
    """Persist file inputs provided from the UI."""

    def __init__(self, workflow: WorkflowYaml) -> None:  # noqa: D401 - workflow unused for symmetry
        self._workflow = workflow

    # ------------------------------------------------------------------
    def execute(self, context: ExecutionContext, params: dict[str, Any], *, step_id: str) -> None:
        input_id = params.get("input_id")
        target = params.get("target")
        if not isinstance(input_id, str) or not isinstance(target, str):
            raise InvalidComponentConfigError("file_uploader requires 'input_id' and 'target'")

        data = context.get(f"inputs.{input_id}")
        if data is None:
            raise ComponentExecutionError(f"Input '{input_id}' was not provided")

        normalized = self._normalize_file(data)
        context.set(target, normalized)
        context.set(f"steps.{step_id}.file", {k: normalized.get(k) for k in ("name", "content_type", "size")})

        view_path = params.get("view_path")
        if isinstance(view_path, str):
            context.set_view(view_path, {k: normalized.get(k) for k in ("name", "content_type", "size")})

    # ------------------------------------------------------------------
    def _normalize_file(self, data: Any) -> dict[str, Any]:
        if isinstance(data, dict):
            name = data.get("name")
            content = data.get("content")
            if not isinstance(name, str) or not isinstance(content, str):
                raise ComponentExecutionError("Uploaded file payload must include name and content")
            content_type = data.get("content_type")
            try:
                decoded = base64.b64decode(content)
            except Exception as exc:  # noqa: PERF203
                raise ComponentExecutionError("Uploaded file content is not valid base64") from exc
            return {
                "name": name,
                "content": content,
                "content_type": content_type or "application/octet-stream",
                "size": len(decoded),
            }
        if isinstance(data, str):
            return {
                "name": data,
                "content": "",
                "content_type": "text/plain",
                "size": 0,
            }
        raise ComponentExecutionError("Unsupported file input format")
