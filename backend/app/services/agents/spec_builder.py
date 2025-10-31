"""Specification builder utilities (skeletal).

Helpers to assemble the aggregated LLM specification produced by Agents 1–4.
"""

from __future__ import annotations

from .models import (
    ClassificationResult,
    ComponentSelection,
    DataFlowDesign,
    LlmSpecification,
    RequirementsSchema,
)


def build_spec(
    requirements: RequirementsSchema,
    classification: ClassificationResult,
    selection: ComponentSelection,
    dataflow: DataFlowDesign,
) -> LlmSpecification:
    """Create an aggregated specification object (thin wrapper)."""
    return LlmSpecification(
        requirements=requirements,
        classification=classification,
        selection=selection,
        dataflow=dataflow,
    )


__all__ = ["build_spec"]
