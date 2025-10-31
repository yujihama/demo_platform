"""Agent 1: Requirements Decomposition (skeletal implementation).

This class provides a minimal `run` method that converts a natural language
description into a structured requirements list. It is intentionally simple and
deterministic to unblock wiring and imports for Phase 2.
"""

from __future__ import annotations

from .models import Requirement, RequirementType, RequirementsSchema


class Agent1Requirements:
    def run(self, description: str) -> RequirementsSchema:
        """Decompose natural language description into structured requirements.

        Note: This is a stub. Future implementations will call an LLM with
        structured output to populate a richer set of requirements.
        """
        # Minimal single-item decomposition to provide a valid structure
        item = Requirement(id="REQ-1", description=description, type=RequirementType.PROCESSING)
        return RequirementsSchema(items=[item])


__all__ = ["Agent1Requirements"]
