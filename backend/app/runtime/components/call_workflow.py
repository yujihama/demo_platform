"""Pipeline component for invoking external workflows (Dify/mock)."""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from ...models.workflow import PipelineStep
from ..context import ExecutionContext
from ..exceptions import PipelineExecutionError
from ..expressions import ExpressionResolver, to_serialisable


class CallWorkflowComponent:
    """Invoke external workflow endpoints and store the response in context."""

    async def run(self, step: PipelineStep, context: ExecutionContext) -> None:
        params: Dict[str, Any] = step.params or {}
        workflow_name = params.get("workflow")
        output_key = params.get("output_key")
        inputs = params.get("inputs", {})
        method = params.get("method", "POST").upper()
        headers = params.get("headers", {})

        if not workflow_name or not output_key:
            raise PipelineExecutionError("call_workflow component requires workflow and output_key")

        provider = context.workflow.workflows.get(workflow_name)
        if provider is None:
            raise PipelineExecutionError(f"Workflow '{workflow_name}' is not defined in workflow.yaml")

        resolver = ExpressionResolver(context.session.context)
        resolved_inputs = resolver.resolve(inputs)

        request_body: Dict[str, Any] = {
            "inputs": to_serialisable(resolved_inputs),
        }

        url = provider.endpoint

        if provider.api_key_env:
            api_key = os.getenv(provider.api_key_env)
            if api_key:
                headers.setdefault("Authorization", f"Bearer {api_key}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, json=request_body, headers=headers)
            response.raise_for_status()
            data = response.json()

        context.set_context_value(output_key, data)


