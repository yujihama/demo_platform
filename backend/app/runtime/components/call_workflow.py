"""Implementation of the `call_workflow` pipeline component."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional

import httpx

from ...models.workflow import WorkflowProvider
from .base import ComponentHandler, ExecutionContext, ExecutionResult
from ..utils import build_path_value, deep_merge, render_template, resolve_path


class CallWorkflowComponent(ComponentHandler):
    """Invoke an external workflow provider such as Dify or its mock."""

    def __init__(self, client_factory: Optional[Callable[[], httpx.AsyncClient]] = None) -> None:
        self._client_factory = client_factory or (lambda: httpx.AsyncClient(timeout=30.0))
        self._client_instance: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client_instance is None:
            self._client_instance = self._client_factory()
        return self._client_instance

    async def execute(
        self,
        context: ExecutionContext,
        payload: Dict[str, Any],
        file: Optional[Any] = None,
    ) -> ExecutionResult:
        params = context.step.params
        workflow_name = params.get("workflow")
        if not workflow_name:
            raise ValueError("call_workflow コンポーネントには workflow の指定が必要です。")

        provider = self._resolve_provider(context, workflow_name)

        template_context = context.engine.build_template_context(context.session)
        input_template = params.get("input_template", {})
        rendered_input = render_template(input_template, template_context)
        if not isinstance(rendered_input, dict):
            raise ValueError("input_template の結果は辞書である必要があります。")

        request_body = params.get("request_body")
        if request_body:
            rendered_body = render_template(request_body, {**template_context, "inputs": rendered_input})
            if not isinstance(rendered_body, dict):
                raise ValueError("request_body の結果は辞書である必要があります。")
        else:
            rendered_body = {"inputs": rendered_input}

        client = await self._get_client()
        headers = self._build_headers(provider)
        response = await client.post(provider.endpoint, json=rendered_body, headers=headers)
        response.raise_for_status()
        data = response.json()

        response_path = params.get("response_path")
        extracted = data
        if response_path:
            merged_context = template_context.copy()
            merged_context.setdefault("response", data)
            extracted = resolve_path(data if isinstance(data, dict) else merged_context, response_path)

        target_key = params.get("target_key")
        private_updates = {}
        if target_key:
            private_updates = build_path_value(target_key, extracted)

        public_updates: Dict[str, Any] = {}
        public_mapping = params.get("public_context")
        if public_mapping:
            public_updates = render_template(public_mapping, {**template_context, "response": extracted})
            if not isinstance(public_updates, dict):
                raise ValueError("public_context の結果は辞書である必要があります。")

        expose_raw_key = params.get("expose_public_key")
        if expose_raw_key:
            public_updates = deep_merge(public_updates, build_path_value(expose_raw_key, extracted))

        context.session.step_outputs[context.step.id] = extracted
        return ExecutionResult(
            public=public_updates,
            private=private_updates,
            step_output={"response": extracted, "raw_response": data},
        )

    def _resolve_provider(self, context: ExecutionContext, workflow_name: str) -> WorkflowProvider:
        try:
            return context.engine.workflow.workflows[workflow_name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ValueError(f"workflows セクションに '{workflow_name}' の定義がありません。") from exc

    def _build_headers(self, provider: WorkflowProvider) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if provider.api_key_env:
            api_key = os.getenv(provider.api_key_env)
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
        return headers

    async def close(self) -> None:
        if self._client_instance is not None:
            await self._client_instance.aclose()
            self._client_instance = None


def create_call_workflow_component(
    client_factory: Optional[Callable[[], httpx.AsyncClient]] = None,
) -> CallWorkflowComponent:
    return CallWorkflowComponent(client_factory=client_factory)
