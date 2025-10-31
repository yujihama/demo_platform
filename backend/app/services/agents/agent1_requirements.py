"""Agent 1: Requirements Decomposition."""

from __future__ import annotations

from typing import Any, Dict

from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from .models import Agent1Output

PROMPT_TEMPLATE = """You are an expert requirements analyst. Your task is to decompose user requirements into structured, actionable items.

Analyze the user's natural language description and break it down into specific requirements. Each requirement should:
- Have a unique ID (e.g., "req_1", "req_2")
- Be clearly described
- Be classified as one of: input, processing, or output

Input requirements: Things the user needs to provide or enter
Processing requirements: Logic, validation, or business rules that need to be applied
Output requirements: Things the system needs to display, generate, or return

Be thorough and ensure all aspects of the user's request are covered."""


class RequirementsDecompositionAgent(BaseAgent[Agent1Output]):
    """Agent that decomposes natural language requirements into structured items."""

    def get_prompt_template(self) -> str:
        return PROMPT_TEMPLATE

    def get_output_model(self) -> type[Agent1Output]:
        return Agent1Output

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format the user's natural language description for the prompt."""
        description = input_data.get("description", "")
        if isinstance(description, dict):
            description = description.get("text", str(description))
        return f"User Requirements:\n\n{description}"
