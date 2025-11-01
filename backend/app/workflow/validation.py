"""Validation helpers for workflow documents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import yaml
from pydantic import ValidationError

from .io import WorkflowLoader
from .models import WorkflowDocument


@dataclass
class WorkflowValidationError:
    code: str
    message: str
    path: str


class WorkflowValidator:
    """Validates workflow YAML documents against the Pydantic schema."""

    @staticmethod
    def validate_yaml(text: str) -> Tuple[WorkflowDocument | None, List[WorkflowValidationError]]:
        try:
            document = WorkflowLoader.from_yaml_text(text)
        except yaml.YAMLError as exc:
            return None, [WorkflowValidationError(code="yaml.parse_error", message=str(exc), path="$")]
        except ValidationError as exc:
            return None, [_convert_error(error) for error in exc.errors()]
        except Exception as exc:  # pylint: disable=broad-except
            return None, [WorkflowValidationError(code="unknown", message=str(exc), path="$")]

        return document, []


def _convert_error(error: dict) -> WorkflowValidationError:
    loc = error.get("loc") or ()
    path = "$." + ".".join(str(part) for part in loc) if loc else "$"
    message = error.get("msg", "validation error")
    type_ = error.get("type", "validation_error")
    return WorkflowValidationError(code=type_, message=message, path=path)

