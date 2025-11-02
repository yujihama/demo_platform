"""for_each pipeline component for transforming lists."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from ...models.workflow import PipelineStep
from ..context import ExecutionContext
from ..exceptions import PipelineExecutionError
from ..expressions import ExpressionResolver, to_serialisable


class ForEachComponent:
    """Transform a collection into a new structure using templates."""

    async def run(self, step: PipelineStep, context: ExecutionContext) -> None:
        params: Dict[str, Any] = step.params or {}
        source_expr = params.get("source")
        template = params.get("template")
        output_key = params.get("output_key")

        if source_expr is None or template is None or not output_key:
            raise PipelineExecutionError("for_each component requires source, template, and output_key")

        resolver = ExpressionResolver(context.session.context)
        source_value = resolver.resolve(source_expr)
        if source_value is None:
            context.set_context_value(output_key, [])
            return

        if not isinstance(source_value, Iterable):
            raise PipelineExecutionError("for_each source must resolve to an iterable")

        results: List[Any] = []
        for item in source_value:
            item_resolver = ExpressionResolver(context.session.context, item=item)
            transformed = item_resolver.resolve(template)
            results.append(to_serialisable(transformed))

        context.set_context_value(output_key, results)


