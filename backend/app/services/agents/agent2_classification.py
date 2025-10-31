"""Agent 2: Application Type Classification."""

from __future__ import annotations

from typing import Any, Dict

from langchain_openai import ChatOpenAI

from .base_agent import BaseAgent
from .models import Agent2Output

PROMPT_TEMPLATE = """You are an expert application architect. Your task is to classify the application type based on the decomposed requirements.

Available application types:
- TYPE_CRUD: Create, Read, Update, Delete operations on data entities
- TYPE_DOCUMENT_PROCESSOR: Processing, parsing, or analyzing documents (invoices, forms, etc.)
- TYPE_VALIDATION: Validating data against rules or business logic
- TYPE_ANALYTICS: Analyzing data to generate insights, reports, or visualizations
- TYPE_CHATBOT: Conversational interfaces with users

Based on the requirements, classify the application and provide:
1. The most appropriate application type
2. A confidence score (0.0 to 1.0)
3. Reasoning for your classification
4. Recommended template structure (e.g., form layout, API endpoints structure)

Be precise and choose the type that best matches the primary purpose of the application."""


class AppTypeClassificationAgent(BaseAgent[Agent2Output]):
    """Agent that classifies the application type based on requirements."""

    def get_prompt_template(self) -> str:
        return PROMPT_TEMPLATE

    def get_output_model(self) -> type[Agent2Output]:
        return Agent2Output

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format the requirements for classification."""
        import json

        requirements = input_data.get("requirements", [])
        summary = input_data.get("summary", "")
        
        formatted = f"Requirements Summary:\n{summary}\n\n"
        formatted += "Detailed Requirements:\n"
        formatted += json.dumps(requirements, ensure_ascii=False, indent=2)
        return formatted
