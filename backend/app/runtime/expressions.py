"""Utility helpers for resolving expressions inside workflow definitions."""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Dict

_EXPRESSION_PATTERN = re.compile(r"^\s*\{\{\s*(?P<expr>[^}]+)\s*\}\}\s*$")


class ExpressionResolver:
    """Resolve templated values using the execution context."""

    def __init__(self, context: Dict[str, Any], item: Any | None = None) -> None:
        self._context = context
        self._item = item

    def resolve(self, value: Any) -> Any:
        if isinstance(value, str):
            match = _EXPRESSION_PATTERN.match(value)
            if match:
                return self._resolve_path(match.group("expr"))
            return value
        if isinstance(value, dict):
            return {key: self.resolve(val) for key, val in value.items()}
        if isinstance(value, list):
            return [self.resolve(element) for element in value]
        return value

    def _resolve_path(self, expr: str) -> Any:
        path = [segment.strip() for segment in expr.split(".") if segment.strip()]
        if not path:
            return None
        root = path[0]
        if root == "context":
            value: Any = self._context
            for segment in path[1:]:
                if isinstance(value, dict):
                    value = value.get(segment)
                else:
                    value = getattr(value, segment, None)
            return value
        if root == "item":
            value = self._item
            for segment in path[1:]:
                if isinstance(value, dict):
                    value = value.get(segment)
                else:
                    value = getattr(value, segment, None)
            return value
        return self._context.get(root)


def decode_base64_to_text(payload: str) -> str:
    """Decode base64 string to UTF-8 text with fallback."""

    raw = base64.b64decode(payload)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="ignore")


def to_serialisable(data: Any) -> Any:
    """Ensure data is JSON serialisable for storage and transport."""

    if isinstance(data, (str, int, float, bool)) or data is None:
        return data
    if isinstance(data, dict):
        return {key: to_serialisable(value) for key, value in data.items()}
    if isinstance(data, list):
        return [to_serialisable(value) for value in data]
    return json.loads(json.dumps(data, default=str))


