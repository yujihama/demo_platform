"""Implementation of the `for_each` pipeline component."""

from __future__ import annotations

from typing import Any, Dict, Iterable

from .base import ComponentHandler, ExecutionContext, ExecutionResult
from ..utils import build_path_value, render_template, resolve_path


class ForEachComponent(ComponentHandler):
    """Map items in the context to a new list using template rendering."""

    async def execute(
        self,
        context: ExecutionContext,
        payload: Dict[str, Any],
        file: Any = None,
    ) -> ExecutionResult:
        params = context.step.params
        items_path = params.get("items_path")
        output_path = params.get("output_path")
        template = params.get("template")

        if not items_path or not output_path or template is None:
            raise ValueError("for_each コンポーネントには items_path, output_path, template の指定が必要です。")

        eval_context = context.engine.build_template_context(context.session)
        items = resolve_path(eval_context, items_path)
        if isinstance(items, str):
            raise ValueError("items_path が指す値はリストまたは配列である必要があります。")
        if not isinstance(items, Iterable):
            raise ValueError("items_path が指す値はリストまたはイテラブルである必要があります。")

        item_name = params.get("item_name", "item")
        result: list[Any] = []
        for item in items:
            local_context = dict(eval_context)
            local_context[item_name] = item
            result.append(render_template(template, local_context))

        public_updates = build_path_value(output_path, result)
        return ExecutionResult(
            public=public_updates,
            step_output={"items": result},
        )


for_each = ForEachComponent()
