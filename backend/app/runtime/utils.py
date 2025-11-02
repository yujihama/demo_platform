"""Utility helpers shared by the workflow runtime engine."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable

from jinja2 import Environment, StrictUndefined

_jinja_env = Environment(autoescape=False)
_jinja_env.undefined = StrictUndefined


def deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Deeply merge two dictionaries without mutating the originals."""

    result = deepcopy(base)
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def build_path_value(path: str, value: Any) -> Dict[str, Any]:
    """Create a nested dictionary representing the dotted path."""

    parts = [part for part in path.split(".") if part]
    if not parts:
        raise ValueError("Path must not be empty")
    root: Dict[str, Any] = {}
    current = root
    for part in parts[:-1]:
        current = current.setdefault(part, {})  # type: ignore[assignment]
        if not isinstance(current, dict):
            raise ValueError(f"Intermediate path '{part}' is not a dictionary")
    current[parts[-1]] = value
    return root


def resolve_path(data: Dict[str, Any], path: str) -> Any:
    """Resolve a dotted path within a nested dictionary."""

    if not path:
        return data
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise KeyError(f"Path '{path}' not found (stopped at '{part}')")
    return current


def render_template(value: Any, variables: Dict[str, Any]) -> Any:
    """Render Jinja templates recursively within arbitrary data structures."""

    if isinstance(value, str):
        if "{{" in value or "{%" in value:
            template = _jinja_env.from_string(value)
            return template.render(variables)
        return value
    if isinstance(value, dict):
        return {key: render_template(val, variables) for key, val in value.items()}
    if isinstance(value, list):
        return [render_template(item, variables) for item in value]
    return value


def truthy(value: Any) -> bool:
    """Interpret a rendered value as boolean."""

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "none"}
    return bool(value)


def flatten_dicts(items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge an iterable of dictionaries."""

    result: Dict[str, Any] = {}
    for item in items:
        result = deep_merge(result, item)
    return result
