"""Component for invoking external workflows such as Dify APIs."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Mapping

import httpx

from ..context import ExecutionContext
from ..exceptions import (
    ComponentExecutionError,
    InvalidComponentConfigError,
    ProviderConfigurationError,
)
from .base import PipelineComponent
from backend.app.models.workflow import WorkflowProvider, WorkflowYaml


class CallWorkflowComponent(PipelineComponent):
    """Invoke configured workflow provider endpoints."""

    def __init__(
        self,
        workflow: WorkflowYaml,
        http_client: httpx.Client,
        *,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._workflow = workflow
        self._http = http_client
        self._timeout = timeout_seconds

    # ------------------------------------------------------------------
    def execute(self, context: ExecutionContext, params: dict[str, Any], *, step_id: str) -> None:
        workflow_name = params.get("workflow")
        if not isinstance(workflow_name, str):
            raise InvalidComponentConfigError("call_workflow requires 'workflow' parameter")

        provider = self._resolve_provider(workflow_name)
        endpoint = self._resolve_endpoint(provider.endpoint)
        method = params.get("method", "POST").upper()
        input_mapping = params.get("input_mapping", {})
        if not isinstance(input_mapping, Mapping):
            raise InvalidComponentConfigError("input_mapping must be a mapping")

        payload = self._build_payload(context, input_mapping)

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if provider.provider == "dify":
            api_key = self._resolve_api_key(provider)
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = self._http.request(
                method,
                endpoint,
                headers=headers,
                content=json.dumps(payload),
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:  # noqa: PERF203
            raise ComponentExecutionError(f"HTTP request failed: {exc}") from exc

        if response.status_code >= 400:
            raise ComponentExecutionError(
                f"Provider request failed with status {response.status_code}: {response.text}",
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:  # noqa: PERF203
            raise ComponentExecutionError("Provider returned invalid JSON") from exc

        context.set(f"steps.{step_id}.response", data)
        output_path = params.get("output_path")
        if isinstance(output_path, str):
            context.set(output_path, data)

        view_path = params.get("view_path")
        if isinstance(view_path, str):
            context.set_view(view_path, data)

    # ------------------------------------------------------------------
    def _resolve_provider(self, workflow_name: str) -> WorkflowProvider:
        provider = self._workflow.workflows.get(workflow_name)
        if provider is None:
            raise ProviderConfigurationError(f"Unknown workflow provider: {workflow_name}")
        return provider

    # ------------------------------------------------------------------
    def _resolve_endpoint(self, endpoint: str) -> str:
        if "$" not in endpoint:
            return endpoint
        pattern = re.compile(r"\$([A-Z0-9_]+)")

        def _replace(match: re.Match[str]) -> str:
            env_name = match.group(1)
            return os.environ.get(env_name, match.group(0))

        return pattern.sub(_replace, endpoint)

    # ------------------------------------------------------------------
    def _resolve_api_key(self, provider: WorkflowProvider) -> str:
        if provider.api_key_env:
            value = os.environ.get(provider.api_key_env)
            if value:
                return value
        value = os.environ.get("DIFY_API_KEY")
        if value:
            return value
        raise ProviderConfigurationError("Dify provider requires API key configuration")

    # ------------------------------------------------------------------
    def _build_payload(self, context: ExecutionContext, mapping: Mapping[str, Any]) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for key, source in mapping.items():
            inputs[key] = self._resolve_value(context, source)
        return {"inputs": inputs}

    # ------------------------------------------------------------------
    def _resolve_value(self, context: ExecutionContext, source: Any) -> Any:
        if isinstance(source, str) and source.startswith("$"):
            return context.get(source[1:], None)
        return source
