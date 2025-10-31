"""Validator agent (skeletal implementation).

Checks a few basic invariants on the aggregated specification. This is a
placeholder to unblock wiring; full catalog/API/type checks will follow later.
"""

from __future__ import annotations

from .models import LlmSpecification, ValidationErrorItem, ValidationResult


class SpecValidator:
    def validate(self, spec: LlmSpecification) -> ValidationResult:
        errors: list[ValidationErrorItem] = []

        # Basic checks ensuring structure is not empty
        if not spec.requirements.items:
            errors.append(
                ValidationErrorItem(code="EMPTY_REQUIREMENTS", message="No requirements provided", path=["requirements", "items"])
            )
        if not spec.selection.components:
            errors.append(
                ValidationErrorItem(code="NO_COMPONENTS", message="No components selected", path=["selection", "components"])
            )
        if errors:
            return ValidationResult(success=False, errors=errors)
        return ValidationResult(success=True)


__all__ = ["SpecValidator"]
