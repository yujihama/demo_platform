"""Base classes and utilities for structured LangChain agents."""

from __future__ import annotations

import logging
import time
from typing import Any, Generic, Type, TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, ValidationError

from ..services.llm_factory import RetryPolicy


logger = logging.getLogger(__name__)

TOutput = TypeVar("TOutput", bound=BaseModel)


class StructuredLLMAgent(Generic[TOutput]):
    """Executes a prompt with structured output and retry semantics."""

    def __init__(
        self,
        name: str,
        llm: BaseChatModel,
        prompt: ChatPromptTemplate,
        output_model: Type[TOutput],
        retry_policy: RetryPolicy,
    ) -> None:
        self._name = name
        self._retry_policy = retry_policy
        self._chain: RunnableSerializable[dict[str, Any], TOutput] = prompt | llm.with_structured_output(output_model)

    def invoke(self, **kwargs: Any) -> TOutput:
        attempt = 0
        delay = self._retry_policy.initial_delay
        while True:
            try:
                return self._chain.invoke(kwargs)
            except ValidationError:
                # Schema issues should surface immediately.
                raise
            except OutputParserException:
                # Structured output failed to parse; considered non-retryable to avoid loops.
                raise
            except Exception as exc:  # pylint: disable=broad-except
                attempt += 1
                if not self._should_retry(exc) or attempt >= self._retry_policy.max_attempts:
                    logger.error("Agent %s failed after %s attempts", self._name, attempt, exc_info=exc)
                    raise

                logger.warning(
                    "Agent %s encountered transient error (%s). Retrying in %.1fs (%s/%s)",
                    self._name,
                    exc,
                    delay,
                    attempt,
                    self._retry_policy.max_attempts,
                )
                time.sleep(delay)
                delay *= self._retry_policy.backoff_multiplier

    @staticmethod
    def _should_retry(exc: Exception) -> bool:
        status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
        if status in {429, 500, 502, 503, 504}:
            return True
        if status in {400, 401, 403, 404}:
            return False

        name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        transient_tokens = ("timeout", "temporarily", "rate limit", "throttle", "retry")
        fatal_tokens = ("invalid", "authentication", "permission", "schema", "parse")

        if any(token in name or token in message for token in transient_tokens):
            return True
        if any(token in name or token in message for token in fatal_tokens):
            return False
        return False

