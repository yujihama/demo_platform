"""Implementation of the file_uploader component."""

from __future__ import annotations

import base64
from typing import Any

from fastapi import UploadFile

from ..context import ExecutionContext, StepState
from ..errors import MissingInputError
from ..utils import resolve_path


async def handle_file_upload(
    context: ExecutionContext,
    params: dict[str, Any],
    file: UploadFile,
) -> StepState:
    """Persist uploaded file metadata inside the execution context."""

    input_key = params.get("input_key")
    if not input_key:
        raise ValueError("file_uploader component requires 'input_key' parameter")

    content = await file.read()
    encoded = base64.b64encode(content).decode("ascii")
    metadata = {
        "filename": file.filename,
        "content_type": file.content_type,
        "content_b64": encoded,
        "size": len(content),
    }
    context.inputs[input_key] = metadata

    state = StepState(status="completed", output=metadata)
    return state


def ensure_file_present(context: ExecutionContext, params: dict[str, Any]) -> None:
    """Validate that the uploaded file exists before executing subsequent steps."""

    input_key = params.get("input_key")
    if not input_key:
        raise ValueError("file_uploader component requires 'input_key' parameter")

    if input_key not in context.inputs:
        raise MissingInputError(f"Input '{input_key}' has not been provided yet")


def get_uploaded_value(context: ExecutionContext, params: dict[str, Any], path: str) -> Any:
    """Resolve a value within the uploaded file metadata."""

    ensure_file_present(context, params)
    base = context.inputs[params["input_key"]]
    return resolve_path(base, path)
