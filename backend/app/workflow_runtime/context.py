"""State management helpers for workflow execution."""

from __future__ import annotations

from typing import Any, Iterable


def _ensure_container(root: dict[str, Any], keys: Iterable[str]) -> dict[str, Any]:
    current = root
    for key in keys:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    return current


def _traverse(root: dict[str, Any], path: str) -> tuple[dict[str, Any], str]:
    if not path:
        raise ValueError("path must be non-empty")
    parts = path.split(".")
    *parents, last = parts
    current = root
    for segment in parents:
        if not isinstance(current, dict) or segment not in current:
            return {}, ""
        current = current[segment]
        if not isinstance(current, dict):
            return {}, ""
    return current, last


class ExecutionContext:
    """Mutable execution context shared between pipeline components."""

    def __init__(self, data: dict[str, Any] | None = None, view: dict[str, Any] | None = None) -> None:
        self.data: dict[str, Any] = data or {}
        self.view: dict[str, Any] = view or {}

    # ------------------------------------------------------------------
    def get(self, path: str, default: Any | None = None) -> Any:
        """Retrieve a value from the context using dotted paths."""

        if not path:
            return default
        parts = path.split(".")
        current: Any = self.data
        for segment in parts:
            if isinstance(current, dict) and segment in current:
                current = current[segment]
            else:
                return default
        return current

    # ------------------------------------------------------------------
    def set(self, path: str, value: Any) -> None:
        """Set a value in the context using dotted paths."""

        if not path:
            raise ValueError("path must be non-empty")
        parts = path.split(".")
        *parents, last = parts
        current = self.data
        if parents:
            current = _ensure_container(self.data, parents)
        current[last] = value

    # ------------------------------------------------------------------
    def set_view(self, path: str, value: Any) -> None:
        """Set a value exposed to the UI."""

        if not path:
            raise ValueError("path must be non-empty")
        if path.startswith("view."):
            path = path[5:]
        parts = path.split(".")
        *parents, last = parts
        current = self.view
        if parents:
            current = _ensure_container(self.view, parents)
        current[last] = value

    # ------------------------------------------------------------------
    def remove(self, path: str) -> None:
        """Remove a value from the context if present."""

        parent, key = _traverse(self.data, path)
        if parent and key and key in parent:
            parent.pop(key, None)

    # ------------------------------------------------------------------
    def snapshot(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return shallow copies of context data and view."""

        return dict(self.data), dict(self.view)
