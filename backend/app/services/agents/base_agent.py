"""Base agent class with common functionality."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, TypeVar

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from ..llm_factory import llm_factory

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    """Base class for all agents."""

    def __init__(self, llm: ChatOpenAI | None = None) -> None:
        """Initialize the agent with an LLM instance."""
        self._llm = llm or llm_factory.create_llm()

    @abstractmethod
    def get_prompt_template(self) -> str:
        """Get the prompt template for this agent."""
        pass

    @abstractmethod
    def get_output_model(self) -> type[T]:
        """Get the Pydantic model for the output."""
        pass

    def run(self, input_data: Dict[str, Any]) -> T:
        """Run the agent and return structured output."""
        prompt_template = self.get_prompt_template()
        output_model = self.get_output_model()

        # Format the prompt
        formatted_input = self._format_input(input_data)
        prompt = ChatPromptTemplate.from_messages([("system", prompt_template), ("user", "{input}")])

        # Create the structured LLM with output schema
        structured_llm = self._llm.with_structured_output(output_model)

        # Create the chain
        chain = prompt | structured_llm

        # Execute with retry logic
        def execute() -> T:
            result = chain.invoke({"input": formatted_input})
            # with_structured_output returns the Pydantic model directly
            if isinstance(result, output_model):
                return result
            # Fallback: convert dict to model if needed
            if isinstance(result, dict):
                return output_model(**result)
            # If it's already the right type, return as-is
            return result

        result = llm_factory.retry_with_backoff(execute)
        logger.info("Agent %s completed successfully", self.__class__.__name__)
        return result

    def _format_input(self, input_data: Dict[str, Any]) -> str:
        """Format input data into a string for the prompt."""
        # Default implementation: convert dict to JSON-like string
        import json

        return json.dumps(input_data, ensure_ascii=False, indent=2)
