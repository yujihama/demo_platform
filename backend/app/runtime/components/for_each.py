"""Implementation of the for_each component."""

from __future__ import annotations

from typing import Any, Dict

from ..context import ExecutionContext, StepState
from ..errors import ComponentExecutionError
from ..utils import resolve_path, set_path


async def for_each(
    context: ExecutionContext,
    params: dict[str, Any],
    engine: "WorkflowEngine",
) -> StepState:
    """Iterate over a list in the execution context and materialise mapped rows."""

    source = params.get("source")
    target = params.get("target")
    mappings: Dict[str, str] = params.get("map", {})

    if not source or not target:
        raise ValueError("for_each component requires both 'source' and 'target' parameters")

    try:
        values = resolve_path({"inputs": context.inputs, "data": context.data}, source)
    except KeyError as exc:
        raise ComponentExecutionError(f"Source path '{source}' could not be resolved") from exc

    if not isinstance(values, list):
        raise ComponentExecutionError("for_each component expects the source to be a list")

    rows = []
    for index, item in enumerate(values):
        row: Dict[str, Any] = {}
        item_context = {"item": item, "index": index, "inputs": context.inputs, "data": context.data}
        for key, path in mappings.items():
            try:
                row[key] = resolve_path(item_context, path)
            except KeyError as exc:
                raise ComponentExecutionError(
                    f"Mapping for key '{key}' with path '{path}' could not be resolved"
                ) from exc
        rows.append(row)

    set_path(context.data, target, rows)
    return StepState(status="completed", output=rows)
