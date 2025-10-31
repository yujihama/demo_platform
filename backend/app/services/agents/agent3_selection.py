"""Agent 3: Component Selection (skeletal implementation).

Select minimal UI components based on requirements and classification.
"""

from __future__ import annotations

from .models import (
    AppType,
    ClassificationResult,
    ComponentSelection,
    RequirementsSchema,
    SelectedComponent,
)


class Agent3Selection:
    def run(
        self,
        requirements: RequirementsSchema,
        classification: ClassificationResult,
    ) -> ComponentSelection:
        """Return a minimal, deterministic component set (stub)."""
        if classification.app_type == AppType.TYPE_VALIDATION:
            components = [
                SelectedComponent(
                    id="cmp-validator",
                    name="ValidatorPanel",
                    props={"title": "Validation"},
                    requirement_ids=[r.id for r in requirements.items],
                    order=1,
                )
            ]
        elif classification.app_type == AppType.TYPE_DOCUMENT_PROCESSOR:
            components = [
                SelectedComponent(
                    id="cmp-uploader",
                    name="FileUploader",
                    props={"accept": "application/pdf"},
                    requirement_ids=[r.id for r in requirements.items],
                    order=1,
                )
            ]
        else:
            components = [
                SelectedComponent(
                    id="cmp-form",
                    name="Form",
                    props={},
                    requirement_ids=[r.id for r in requirements.items],
                    order=1,
                )
            ]
        return ComponentSelection(components=components)


__all__ = ["Agent3Selection"]
