"""Agent 3: Component Selection."""

from __future__ import annotations

from typing import Any, Dict

from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from .models import Agent3Output

PROMPT_TEMPLATE = """You are an expert UI/UX designer. Your task is to select appropriate UI components from a catalog to fulfill the requirements.

You will receive:
1. Decomposed requirements
2. Application type
3. UI components catalog

For each requirement, select the appropriate UI components that will fulfill it. Each component should:
- Come from the provided catalog
- Be positioned in the appropriate step and section of the wizard
- Have appropriate properties (labels, placeholders, types, etc.)
- Map to at least one requirement ID

Ensure that all requirements are fulfilled by at least one component. Components should be organized logically across wizard steps."""


class ComponentSelectionAgent(BaseAgent[Agent3Output]):
    """Agent that selects UI components from the catalog based on requirements."""

    def __init__(self, ui_parts_catalog: Dict[str, Any] | None = None, llm: ChatOpenAI | None = None) -> None:
        """Initialize with UI parts catalog."""
        super().__init__(llm)
        self._ui_parts_catalog = ui_parts_catalog or {}

    def get_prompt_template(self) -> str:
        return PROMPT_TEMPLATE

    def get_output_model(self) -> type[Agent3Output]:
        return Agent3Output

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format the requirements, app type, and catalog for component selection."""
        import json

        requirements = input_data.get("requirements", [])
        app_type = input_data.get("app_type", "")
        catalog = self._ui_parts_catalog

        formatted = f"Application Type: {app_type}\n\n"
        formatted += "Requirements:\n"
        formatted += json.dumps(requirements, ensure_ascii=False, indent=2)
        formatted += "\n\nUI Components Catalog:\n"
        formatted += json.dumps(catalog, ensure_ascii=False, indent=2)
        return formatted
