"""Agent 4: Data Flow Design."""

from __future__ import annotations

from typing import Any, Dict

from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from .models import Agent4Output

PROMPT_TEMPLATE = """You are an expert system architect. Your task is to design the data flow between UI components and backend services.

Based on the selected components and requirements, design a data flow that:
1. Defines how data moves between components
2. Specifies triggers (form submissions, button clicks, etc.)
3. Maps component outputs to inputs
4. Defines API calls where needed
5. Ensures type safety throughout the flow
6. Ensures all requirements are fulfilled

Each step in the data flow should:
- Have a unique step ID
- Define what triggers it
- Specify source and target components
- Define any API calls (with method, path, request/response types)
- List state variables affected
- Include type definitions

Ensure the flow is complete and all component interactions are properly defined."""


class DataFlowDesignAgent(BaseAgent[Agent4Output]):
    """Agent that designs the data flow between components."""

    def get_prompt_template(self) -> str:
        return PROMPT_TEMPLATE

    def get_output_model(self) -> type[Agent4Output]:
        return Agent4Output

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format the requirements, app type, and components for data flow design."""
        import json

        requirements = input_data.get("requirements", [])
        app_type = input_data.get("app_type", "")
        components = input_data.get("components", [])

        formatted = f"Application Type: {app_type}\n\n"
        formatted += "Requirements:\n"
        formatted += json.dumps(requirements, ensure_ascii=False, indent=2)
        formatted += "\n\nSelected Components:\n"
        formatted += json.dumps(components, ensure_ascii=False, indent=2)
        return formatted
