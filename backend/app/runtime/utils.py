"""Utility helpers for workflow runtime."""

from __future__ import annotations

from typing import Any, Iterable


def resolve_path(data: Any, path: str) -> Any:
    """Resolve dotted attribute access within dictionaries and lists."""

    if not path:
        return data

    current: Any = data
    for segment in path.split("."):
        if isinstance(current, dict):
            current = current.get(segment)
        elif isinstance(current, list):
            try:
                index = int(segment)
            except ValueError as exc:  # pragma: no cover - defensive branch
                raise KeyError(f"List index must be an integer: {segment}") from exc
            try:
                current = current[index]
            except IndexError as exc:  # pragma: no cover - defensive branch
                raise KeyError(f"List index out of range: {segment}") from exc
        else:
            raise KeyError(f"Cannot resolve segment '{segment}' in non-container type")
    return current


def set_path(data: dict[str, Any], path: str, value: Any) -> None:
    """Set a value within nested dictionaries using dot notation."""

    segments = path.split(".") if path else []
    current: Any = data
    for segment in segments[:-1]:
        if segment not in current or not isinstance(current[segment], dict):
            current[segment] = {}
        current = current[segment]
    if segments:
        current[segments[-1]] = value
    else:
        raise ValueError("Cannot set value for empty path")


def ensure_iterable(value: Any) -> Iterable[Any]:
    """Ensure the provided value is iterable."""

    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return value
    return [value]
