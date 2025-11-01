"""Factory that produces mock agents or LangChain-powered LLM clients."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..config import ConfigManager, config_manager
from .mock_agent import MockAgent


logger = logging.getLogger(__name__)


def _or_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_multiplier: float = 2.0


class MockStructuredChatModel:
    """Deterministic mock chat model used to simulate LLM responses."""

    def __init__(self) -> None:
        self._analysis: Dict[str, Any] | None = None
        self._plan: Dict[str, Any] | None = None
        self._attempts = 0

    def with_structured_output(self, output_model: Any) -> Any:  # noqa: ANN401
        outer = self

        class _MockRunnable:
            def invoke(self, prompt_value: Any) -> Any:  # noqa: ANN401
                return outer._invoke(output_model, prompt_value)

        return _MockRunnable()

    def _invoke(self, output_model: Any, prompt_value: Any) -> Any:  # noqa: ANN401
        name = getattr(output_model, "__name__", "")
        if name == "AnalystResult":
            return self._mock_analysis(output_model)
        if name == "ArchitecturePlan":
            return self._mock_plan(output_model)
        if name == "WorkflowDraft":
            return self._mock_workflow_draft(output_model)
        if name == "ValidatorFeedback":
            return self._mock_validator_feedback(output_model, prompt_value)
        raise ValueError(f"Unsupported mock structured output model: {name}")

    def _mock_analysis(self, model: Any) -> Any:  # noqa: ANN401
        analysis = {
            "primary_goal": "?????????",
            "domain_context": "?????????",
            "requirements": [
                {
                    "id": "REQ-1",
                    "title": "??????????",
                    "detail": "????????PDF??????????",
                    "category": "input",
                    "acceptance_criteria": ["PDF????????"],
                },
                {
                    "id": "REQ-2",
                    "title": "AI???",
                    "detail": "?????????????AI????????",
                    "category": "process",
                    "acceptance_criteria": ["??????????????"],
                },
                {
                    "id": "REQ-3",
                    "title": "?????",
                    "detail": "??????????????",
                    "category": "output",
                    "acceptance_criteria": ["????????????"],
                },
            ],
            "risks": ["Dify API ??????"],
            "sample_inputs": ["invoice-001.pdf"],
        }
        self._analysis = analysis
        return model(**analysis)

    def _mock_plan(self, model: Any) -> Any:  # noqa: ANN401
        plan = {
            "title": "????????",
            "summary": "?????????????2??????",
            "ui_steps": [
                {
                    "id": "upload_step",
                    "title": "??????",
                    "description": "???PDF??????",
                    "components": ["invoice_upload", "run_button"],
                    "success_transition": "result_step",
                },
                {
                    "id": "result_step",
                    "title": "????",
                    "description": "????????????",
                    "components": ["result_table"],
                    "success_transition": None,
                },
            ],
            "pipeline": [
                {
                    "id": "call_validation",
                    "type": "call_workflow",
                    "description": "Dify??????????????",
                    "uses_provider": "dify_invoice",
                    "inputs": ["file_url"],
                    "outputs": ["validation_result"],
                },
                {
                    "id": "summarise_result",
                    "type": "transform",
                    "description": "?????UI?????",
                    "uses_provider": None,
                    "inputs": ["validation_result"],
                    "outputs": ["summary"],
                },
            ],
            "workflows": [
                {
                    "id": "dify_invoice",
                    "provider_type": "dify",
                    "endpoint": "https://mock.dify/api",
                    "description": "????????",
                }
            ],
        }
        self._plan = plan
        return model(**plan)

    def _mock_workflow_draft(self, model: Any) -> Any:  # noqa: ANN401
        self._attempts += 1
        yaml = (
            "version: '1'\n"
            "info:\n"
            "  name: ???????\n"
            "  summary: ??????????????workflow\n"
            "  version: 1.0.0\n"
            "workflows:\n"
            "  - id: dify_invoice\n"
            "    provider: dify\n"
            "    endpoint: https://mock.dify/api\n"
            "    method: POST\n"
            "pipeline:\n"
            "  - id: call_validation\n"
            "    type: call_workflow\n"
            "    title: ????????\n"
            "    with:\n"
            "      provider_id: dify_invoice\n"
            "      input:\n"
            "        file_url: '{{ context.upload_step.outputs.file_url }}'\n"
            "    on_success:\n"
            "      - summarise_result\n"
            "  - id: summarise_result\n"
            "    type: transform\n"
            "    title: ????\n"
            "    with:\n"
            "      expression: >-\n"
            "        {\"status\": context.call_validation.outputs.validation_result.status}\n"
            "ui:\n"
            "  layout: wizard\n"
            "  steps:\n"
            "    - id: upload_step\n"
            "      title: ??????\n"
            "      description: ???PDF??????\n"
            "      components:\n"
            "        - id: invoice_upload\n"
            "          type: file_upload\n"
            "          label: ???\n"
            "        - id: run_button\n"
            "          type: button\n"
            "          label: ?????\n"
            "    - id: result_step\n"
            "      title: ??\n"
            "      description: ???????\n"
            "      components:\n"
            "        - id: result_table\n"
            "          type: table\n"
            "          label: ????\n"
        )
        notes = ["???LLM?????"]
        return model(workflow_yaml=yaml, notes=notes)

    def _mock_validator_feedback(self, model: Any, prompt_value: Any) -> Any:  # noqa: ANN401
        text = str(prompt_value)
        if "missing" in text.lower():
            return model(is_valid=False, errors=["provider id ???"], suggestions=["workflows ? provider ?????????"])
        return model(is_valid=True, errors=[], suggestions=["zip ????????? .env ?????????"])

class LLMFactory:
    def __init__(self, cfg: ConfigManager = config_manager) -> None:
        self._cfg = cfg

    def create_mock_agent(self, spec_id: str) -> MockAgent:
        llm_cfg = self._cfg.llm
        mock_entry: Dict[str, Any] = llm_cfg.mocks.get(spec_id) or {}
        response_path = mock_entry.get("response_path") or self._cfg.features.agents.mock_spec_path
        return MockAgent(Path(response_path).parent if Path(response_path).is_file() else Path(response_path))

    def create_chat_model(self) -> BaseChatModel:
        llm_cfg = self._cfg.llm
        defaults = llm_cfg.defaults
        provider = llm_cfg.provider

        if provider == "mock":
            logger.debug("Using mock structured chat model for LLM pipeline")
            return MockStructuredChatModel()

        if provider == "openai":
            provider_cfg = llm_cfg.get_openai_config()
            if not provider_cfg.enabled:
                raise RuntimeError("OpenAI provider is not enabled in llm.yaml")
            return ChatOpenAI(
                model=self._select_model(provider_cfg.model, defaults.model),
                temperature=self._select_temperature(provider_cfg.temperature, defaults.temperature),
                api_key=provider_cfg.api_key,
                organization=_or_none(provider_cfg.organization),
                base_url=_or_none(provider_cfg.base_url),
            )

        if provider == "azure_openai":
            provider_cfg = llm_cfg.get_azure_openai_config()
            if not provider_cfg.enabled:
                raise RuntimeError("Azure OpenAI provider is not enabled in llm.yaml")
            return ChatOpenAI(
                model=self._select_model(provider_cfg.model, defaults.model),
                temperature=self._select_temperature(provider_cfg.temperature, defaults.temperature),
                api_key=provider_cfg.api_key,
                azure_endpoint=provider_cfg.endpoint,
                azure_deployment=provider_cfg.deployment,
                azure_api_version=provider_cfg.api_version,
            )

        raise RuntimeError(f"LLM provider '{provider}' does not support LangChain integration")

    def get_retry_policy(self) -> RetryPolicy:
        return RetryPolicy()

    @staticmethod
    def _select_model(candidate: Optional[str], default: str) -> str:
        model_name = candidate or default
        if not model_name:
            raise ValueError("Model name must be configured for the active LLM provider")
        return model_name

    @staticmethod
    def _select_temperature(candidate: Optional[float], default: float) -> float:
        return candidate if candidate is not None else default


llm_factory = LLMFactory()

