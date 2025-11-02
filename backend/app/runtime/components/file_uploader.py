"""File uploader pipeline component."""

from __future__ import annotations

import base64
from typing import Any, Dict

from ...models.workflow import PipelineStep
from ..context import ExecutionContext
from ..exceptions import PipelineExecutionError, PipelineWait
from ..expressions import decode_base64_to_text


class FileUploaderComponent:
    """Extract uploaded file content into the execution context."""

    async def run(self, step: PipelineStep, context: ExecutionContext) -> None:
        params: Dict[str, Any] = step.params or {}
        component_id = params.get("component_id")
        output_key = params.get("output_key")
        required = params.get("required", True)
        mode = params.get("mode", "text")

        if not component_id or not output_key:
            raise PipelineExecutionError("file_uploader component requires component_id and output_key")

        state = context.get_component_value(component_id)
        if state is None or state.value is None:
            if required:
                raise PipelineWait([component_id])
            context.set_context_value(output_key, None)
            return

        value = state.value
        if not isinstance(value, dict) or "data" not in value:
            raise PipelineExecutionError(f"Invalid payload for component {component_id}")

        payload = value["data"]
        if mode == "text":
            text = decode_base64_to_text(payload)
            context.set_context_value(output_key, text)
        else:
            raw = base64.b64decode(payload)
            context.set_context_value(output_key, raw)

        context.set_component_value(component_id, value, status="consumed")


