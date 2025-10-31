"""Agent 4: Data Flow Design (skeletal implementation).

Design a minimal data flow connecting selected components.
"""

from __future__ import annotations

from .models import (
    ComponentSelection,
    DataFlowDesign,
    FlowStep,
    RequirementsSchema,
    StateVariable,
)


class Agent4DataFlow:
    def run(self, selection: ComponentSelection, requirements: RequirementsSchema) -> DataFlowDesign:
        """Create a minimal data flow (stub)."""
        # A single state variable and a single step referencing the first component
        state = [StateVariable(name="result", type="string")]
        steps: list[FlowStep] = []
        if selection.components:
            first = selection.components[0]
            steps.append(
                FlowStep(
                    id="flow-1",
                    trigger="onSubmit",
                    source_component=first.id,
                    target_component=first.id,
                    action="updateState",
                )
            )
        return DataFlowDesign(steps=steps, state=state)


__all__ = ["Agent4DataFlow"]
