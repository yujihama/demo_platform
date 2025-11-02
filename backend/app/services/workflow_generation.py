"""Reusable workflow generation orchestration utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict

from ..agents.workflow_agents import AnalystAgent, ArchitectAgent
from ..services.workflow_validator import SelfCorrectionLoop, WorkflowValidator
from .llm_factory import LLMFactory, llm_factory

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkflowGenerationResult:
    """Aggregated result of the workflow generation pipeline."""

    yaml_content: str
    analysis: Any
    architecture: Any
    validation: Dict[str, Any]


class WorkflowGenerator:
    """High-level facade orchestrating the multi-agent workflow generation."""

    def __init__(
        self,
        factory: LLMFactory | None = None,
        validator: WorkflowValidator | None = None,
        *,
        max_iterations: int = 3,
    ) -> None:
        self._factory = factory or llm_factory
        self._validator = validator or WorkflowValidator(self._factory)
        self._max_iterations = max_iterations

    def generate(
        self,
        prompt: str,
        *,
        on_analysis: Callable[[Any], None] | None = None,
        on_architecture: Callable[[Any], None] | None = None,
        on_yaml: Callable[[str], None] | None = None,
        on_validation: Callable[[Dict[str, Any]], None] | None = None,
    ) -> WorkflowGenerationResult:
        """Generate a workflow.yaml from natural language requirements."""

        normalized_prompt = (prompt or "").strip()
        if not normalized_prompt:
            raise ValueError("workflow.yaml を生成するには要件のプロンプトが必要です")

        llm = self._factory.create_chat_model()
        retry_policy = self._factory.get_retry_policy()

        logger.info("Starting workflow generation analysis phase")
        analyst = AnalystAgent(llm, retry_policy)
        analysis_result = analyst.run(normalized_prompt)
        if on_analysis:
            on_analysis(analysis_result)

        logger.info("Starting workflow generation architecture phase")
        architect = ArchitectAgent(llm, retry_policy)
        architecture_result = architect.run(analysis_result)
        if on_architecture:
            on_architecture(architecture_result)

        correction_loop = SelfCorrectionLoop(
            self._factory,
            self._validator,
            max_iterations=self._max_iterations,
        )

        logger.info("Starting workflow.yaml generation with self-correction")
        yaml_content, success, errors = correction_loop.generate_with_correction(
            analysis_result,
            architecture_result,
        )

        if not success:
            message = "; ".join(errors) if errors else "不明な理由"
            raise RuntimeError(f"workflow.yaml の生成に失敗しました: {message}")

        if on_yaml:
            on_yaml(yaml_content)

        logger.info("Validating generated workflow.yaml")
        validation_result = self._validator.validate_complete(yaml_content)
        if not validation_result.get("valid"):
            errors = validation_result.get("all_errors", [])
            message = "; ".join(errors) if errors else "不明なエラー"
            raise RuntimeError(f"workflow.yaml の検証に失敗しました: {message}")

        if on_validation:
            on_validation(validation_result)

        return WorkflowGenerationResult(
            yaml_content=yaml_content,
            analysis=analysis_result,
            architecture=architecture_result,
            validation=validation_result,
        )

