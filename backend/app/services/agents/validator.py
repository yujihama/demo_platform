"""Validator Agent for specification validation."""

from __future__ import annotations

from typing import Any, Dict, List

from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from .models import ValidatorOutput

PROMPT_TEMPLATE = """You are a specification validator. Your task is to verify that the generated application specification is correct and complete.

Validation rules to check:
1. All components exist in the UI parts catalog
2. API endpoints are properly defined (if Dify catalog is provided, check against it)
3. Type consistency: component outputs match component inputs where data flows
4. No circular dependencies in the data flow
5. All requirements from Agent 1 are fulfilled by at least one component

For each validation error found:
- Specify which rule failed
- Provide a clear error message
- Include the component ID if applicable

Return validation results with:
- is_valid: true if all checks pass, false otherwise
- errors: list of validation errors (empty if valid)
- warnings: list of non-critical issues"""


class ValidatorAgent(BaseAgent[ValidatorOutput]):
    """Agent that validates the generated specification."""

    def __init__(
        self,
        ui_parts_catalog: Dict[str, Any] | None = None,
        dify_catalog: Dict[str, Any] | None = None,
        llm: ChatOpenAI | None = None,
    ) -> None:
        """Initialize with catalogs."""
        super().__init__(llm)
        self._ui_parts_catalog = ui_parts_catalog or {}
        self._dify_catalog = dify_catalog or {}

    def get_prompt_template(self) -> str:
        return PROMPT_TEMPLATE

    def get_output_model(self) -> type[ValidatorOutput]:
        return ValidatorOutput

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format the complete specification for validation."""
        import json

        requirements = input_data.get("requirements", [])
        app_type = input_data.get("app_type", "")
        components = input_data.get("components", [])
        data_flow = input_data.get("data_flow", [])

        formatted = "Complete Application Specification:\n\n"
        formatted += f"Application Type: {app_type}\n\n"
        formatted += "Requirements:\n"
        formatted += json.dumps(requirements, ensure_ascii=False, indent=2)
        formatted += "\n\nComponents:\n"
        formatted += json.dumps(components, ensure_ascii=False, indent=2)
        formatted += "\n\nData Flow:\n"
        formatted += json.dumps(data_flow, ensure_ascii=False, indent=2)
        formatted += "\n\nUI Parts Catalog:\n"
        formatted += json.dumps(self._ui_parts_catalog, ensure_ascii=False, indent=2)
        if self._dify_catalog:
            formatted += "\n\nDify Catalog:\n"
            formatted += json.dumps(self._dify_catalog, ensure_ascii=False, indent=2)
        return formatted
