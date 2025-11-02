"""Component that transforms collections using declarative mappings."""

from __future__ import annotations

from typing import Any

from jinja2 import Environment, StrictUndefined

from ..context import ExecutionContext
from ..exceptions import ComponentExecutionError, InvalidComponentConfigError
from .base import PipelineComponent
from ...models.workflow import WorkflowYaml


_jinja_env = Environment(undefined=StrictUndefined, autoescape=False, trim_blocks=True, lstrip_blocks=True)


class ForEachComponent(PipelineComponent):
    """Apply a mapping template to each item in a collection."""

    def __init__(self, workflow: WorkflowYaml) -> None:  # noqa: D401 - workflow unused for symmetry
        self._workflow = workflow

    # ------------------------------------------------------------------
    def execute(self, context: ExecutionContext, params: dict[str, Any], *, step_id: str) -> None:
        source_path = params.get("source")
        target_path = params.get("target")
        mapping = params.get("map")

        if not isinstance(source_path, str) or not isinstance(target_path, str):
            raise InvalidComponentConfigError("for_each requires 'source' and 'target'")
        if mapping is not None and not isinstance(mapping, dict):
            raise InvalidComponentConfigError("map parameter must be an object")

        items = context.get(source_path, [])
        if not isinstance(items, list):
            raise ComponentExecutionError("for_each source must resolve to a list")

        result: list[Any] = []
        for item in items:
            if mapping:
                result.append(self._apply_mapping(mapping, item, context))
            else:
                result.append(item)

        context.set(target_path, result)
        context.set(f"steps.{step_id}.items", result)

        view_path = params.get("view_path")
        if isinstance(view_path, str):
            context.set_view(view_path, result)

    # ------------------------------------------------------------------
    def _apply_mapping(self, mapping: dict[str, Any], item: Any, context: ExecutionContext) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, template in mapping.items():
            if isinstance(template, str):
                output[key] = self._render_template(template, item, context)
            else:
                output[key] = template
        return output

    # ------------------------------------------------------------------
    def _render_template(self, template: str, item: Any, context: ExecutionContext) -> Any:
        try:
            compiled = _jinja_env.from_string(template)
            return compiled.render(item=item, context=context.data)
        except Exception as exc:  # noqa: PERF203
            raise ComponentExecutionError(f"Failed to render template '{template}': {exc}") from exc
