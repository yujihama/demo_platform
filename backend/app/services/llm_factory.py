"""LLM factory supporting both mock and real LLM providers."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_openai import ChatOpenAI
from openai import OpenAIError

from ..config import ConfigManager, config_manager
from .mock_agent import MockAgent

logger = logging.getLogger(__name__)


class LLMFactory:
    """Factory for creating LLM instances and agents."""

    def __init__(self, cfg: ConfigManager = config_manager) -> None:
        self._cfg = cfg
        self._llm_instance: Optional[ChatOpenAI] = None

    def create_mock_agent(self, spec_id: str) -> MockAgent:
        """Create a mock agent that returns deterministic specs."""
        llm_cfg = self._cfg.llm
        mock_entry: Dict[str, Any] = llm_cfg.mocks.get(spec_id) or {}
        response_path = mock_entry.get("response_path") or self._cfg.features.agents.mock_spec_path
        return MockAgent(Path(response_path).parent if Path(response_path).is_file() else Path(response_path))

    def create_llm(self) -> ChatOpenAI:
        """Create a LangChain ChatOpenAI instance based on configuration."""
        if self._llm_instance is not None:
            return self._llm_instance

        llm_cfg = self._cfg.llm
        provider = llm_cfg.provider
        defaults = llm_cfg.defaults

        if provider == "mock":
            raise ValueError("Cannot create LLM instance when provider is 'mock'. Use create_mock_agent instead.")

        provider_config = llm_cfg.providers.get(provider)
        if not provider_config or not provider_config.get("enabled"):
            raise ValueError(f"Provider '{provider}' is not enabled or not configured")

        if provider == "openai":
            api_key = provider_config.get("api_key")
            if not api_key:
                raise ValueError("OpenAI API key is required")
            self._llm_instance = ChatOpenAI(
                model=defaults.model,
                temperature=defaults.temperature,
                api_key=api_key,
            )
        elif provider == "azure_openai":
            api_key = provider_config.get("api_key")
            endpoint = provider_config.get("endpoint")
            deployment_name = provider_config.get("deployment_name")
            api_version = provider_config.get("api_version", "2024-02-15-preview")

            if not api_key or not endpoint or not deployment_name:
                raise ValueError("Azure OpenAI requires api_key, endpoint, and deployment_name")

            self._llm_instance = ChatOpenAI(
                model=deployment_name,
                temperature=defaults.temperature,
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        logger.info("Created LLM instance for provider: %s", provider)
        return self._llm_instance

    def retry_with_backoff(
        self,
        func,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ) -> Any:
        """Execute a function with exponential backoff retry logic.

        Args:
            func: The function to execute
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff

        Returns:
            The result of the function call

        Raises:
            Exception: The last exception if all retries are exhausted
        """
        last_exception = None
        delay = initial_delay

        for attempt in range(1, max_attempts + 1):
            try:
                return func()
            except OpenAIError as e:
                last_exception = e
                # Don't retry on validation errors (400, 401)
                if hasattr(e, "status_code") and e.status_code in (400, 401):
                    logger.error("Non-retryable error (status %s): %s", e.status_code, str(e))
                    raise

                if attempt < max_attempts:
                    logger.warning(
                        "LLM API call failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt,
                        max_attempts,
                        str(e),
                        delay,
                    )
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
                else:
                    logger.error("LLM API call failed after %d attempts: %s", max_attempts, str(e))
            except Exception as e:
                # For other exceptions, check if they're transient
                if attempt < max_attempts and self._is_transient_error(e):
                    logger.warning(
                        "Transient error (attempt %d/%d): %s. Retrying in %.1fs...",
                        attempt,
                        max_attempts,
                        str(e),
                        delay,
                    )
                    last_exception = e
                    time.sleep(delay)
                    delay = min(delay * exponential_base, max_delay)
                else:
                    # Non-transient or last attempt
                    raise

        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected error in retry logic")

    @staticmethod
    def _is_transient_error(exception: Exception) -> bool:
        """Check if an exception represents a transient error that should be retried."""
        error_str = str(exception).lower()
        transient_keywords = ["timeout", "connection", "503", "429", "rate limit", "server error"]
        return any(keyword in error_str for keyword in transient_keywords)


llm_factory = LLMFactory()

