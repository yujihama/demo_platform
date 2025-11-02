"""Implementation of the call_workflow component."""

from __future__ import annotations

import os
from typing import Any

import httpx

from ..context import ExecutionContext, StepState
from ..errors import ComponentExecutionError
from ..utils import resolve_path


async def call_workflow(
    context: ExecutionContext,
    params: dict[str, Any],
    engine: "WorkflowEngine",
) -> StepState:
    """Invoke an external workflow provider."""

    workflow_key = params.get("workflow")
    if not workflow_key:
        raise ValueError("call_workflow component requires 'workflow' parameter")

    provider = context.workflow.workflows.get(workflow_key)
    if provider is None:
        raise ComponentExecutionError(f"Workflow provider '{workflow_key}' is not defined")

    input_mapping: dict[str, str] = params.get("input_mapping", {})
    payload: dict[str, Any] = {}
    context_dict = {
        "inputs": context.inputs,
        "data": context.data,
        "steps": {key: state.to_dict() for key, state in context.steps.items()},
    }

    for field, path in input_mapping.items():
        try:
            payload[field] = resolve_path(context_dict, path)
        except KeyError as exc:
            raise ComponentExecutionError(
                f"Failed to resolve input '{path}' for field '{field}'"
            ) from exc

    headers: dict[str, str] = params.get("headers", {})
    if provider.api_key_env:
        api_key = os.environ.get(provider.api_key_env)
        if api_key:
            headers.setdefault("Authorization", f"Bearer {api_key}")

    method = params.get("method", "POST").upper()

    async with engine.http_client as client:
        try:
            response = await client.request(method, provider.endpoint, json=payload, headers=headers)
        except httpx.HTTPError as exc:  # pragma: no cover - network failures
            raise ComponentExecutionError(f"Failed to call workflow endpoint: {exc}") from exc

    if response.status_code >= 400:
        raise ComponentExecutionError(
            f"Workflow call failed with status {response.status_code}: {response.text}"
        )

    try:
        data = response.json()
    except ValueError as exc:  # pragma: no cover - unexpected payloads
        raise ComponentExecutionError("Workflow response is not valid JSON") from exc

    output_key = params.get("output_key") or workflow_key
    context.data[output_key] = data

    state = StepState(status="completed", output=data)
    return state
