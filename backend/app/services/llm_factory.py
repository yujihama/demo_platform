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
        self._last_prompt: str = ""
        self._app_type: str = "TYPE_DOCUMENT_PROCESSOR"
        self._requirements: Dict[str, Any] | None = None
        self._components: Dict[str, Any] | None = None
        self._validation_attempts = 0
        self._force_retry = False
        self._force_failure = False

    def with_structured_output(self, output_model: Any) -> Any:  # noqa: ANN401
        outer = self

        class _MockRunnable:
            def invoke(self, prompt_value: Any) -> Any:  # noqa: ANN401
                return outer._invoke(output_model, prompt_value)

        return _MockRunnable()

    def _invoke(self, output_model: Any, prompt_value: Any) -> Any:  # noqa: ANN401
        name = getattr(output_model, "__name__", "")
        text = self._extract_text(prompt_value)
        if name == "RequirementsDecompositionResult":
            return output_model(**self._build_requirements(text))
        if name == "AppTypeClassificationResult":
            return output_model(**self._build_classification())
        if name == "ComponentSelectionResult":
            result = self._build_components()
            self._components = result
            return output_model(**result)
        if name == "DataFlowDesignResult":
            return output_model(**self._build_data_flow())
        if name == "ValidationResult":
            return output_model(**self._build_validation())
        raise ValueError(f"Unsupported mock structured output model: {name}")

    @staticmethod
    def _extract_text(prompt_value: Any) -> str:  # noqa: ANN401
        try:
            messages = prompt_value.messages  # type: ignore[attr-defined]
            if messages:
                content = messages[-1].content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = []
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            parts.append(str(item["text"]))
                    return "\n".join(parts)
        except AttributeError:
            pass
        return str(prompt_value)

    def _build_requirements(self, formatted_prompt: str) -> Dict[str, Any]:
        prompt = self._parse_user_prompt(formatted_prompt)
        self._last_prompt = prompt
        lowered = prompt.lower()
        self._app_type = (
            "TYPE_VALIDATION"
            if any(keyword in lowered for keyword in ["validate", "validation", "quality", "review", "check"])
            else "TYPE_DOCUMENT_PROCESSOR"
        )
        self._force_retry = "force retry" in lowered
        self._force_failure = "force failure" in lowered
        self._validation_attempts = 0

        if self._app_type == "TYPE_VALIDATION":
            requirements = [
                {
                    "id": "VAL-1",
                    "category": "INPUT",
                    "title": "Capture validation request",
                    "description": "Allow operators to provide record identifiers and optional context for validation.",
                    "acceptance_criteria": ["Supports multiple record identifiers in a single submission"],
                },
                {
                    "id": "VAL-2",
                    "category": "PROCESSING",
                    "title": "Run business rule checks",
                    "description": "Execute business rules and thresholds against submitted data.",
                    "acceptance_criteria": ["Validation completes within five seconds", "Returns failing rules with severity"],
                },
                {
                    "id": "VAL-3",
                    "category": "OUTPUT",
                    "title": "Present validation result",
                    "description": "Summarise pass/fail status and recommended next steps for the operator.",
                    "acceptance_criteria": ["Clearly highlight critical failures"],
                },
            ]
            summary = "Automated validation workflow for business data"
            primary_goal = "Validate incoming records against business rules and surface issues quickly"
        else:
            requirements = [
                {
                    "id": "REQ-1",
                    "category": "INPUT",
                    "title": "Upload invoice document",
                    "description": "Allow users to upload invoice documents in PDF or image format.",
                    "acceptance_criteria": ["Supports PDF and image formats"],
                },
                {
                    "id": "REQ-2",
                    "category": "PROCESSING",
                    "title": "Extract invoice fields",
                    "description": "Parse uploaded invoices to extract vendor, amount, date, and currency fields.",
                    "acceptance_criteria": ["Returns structured JSON with extracted fields"],
                },
                {
                    "id": "REQ-3",
                    "category": "OUTPUT",
                    "title": "Display validation summary",
                    "description": "Expose extracted values and anomalies for finance reviewers to confirm.",
                    "acceptance_criteria": ["Highlights anomalies in the summary"],
                },
            ]
            summary = "Automated document processing workflow for invoices"
            primary_goal = "Automate extraction and validation of invoice data"

        result = {
            "summary": summary,
            "primary_goal": primary_goal,
            "requirements": requirements,
        }
        self._requirements = result
        return result

    def _build_classification(self) -> Dict[str, Any]:
        supporting = [req["id"] for req in (self._requirements or {}).get("requirements", [])]
        template = (
            "validation-workflow-basic"
            if self._app_type == "TYPE_VALIDATION"
            else "document-processor-basic"
        )
        return {
            "app_type": self._app_type,
            "confidence": 0.92,
            "rationale": "Keyword based classification",
            "recommended_template": template,
            "supporting_requirements": supporting,
        }

    def _build_components(self) -> Dict[str, Any]:
        if self._app_type == "TYPE_VALIDATION":
            components = [
                {
                    "component_id": "text_input",
                    "slot": "main",
                    "props": {"label": "Record ID", "binding": "record_id", "required": True},
                    "fulfills": ["VAL-1"],
                },
                {
                    "component_id": "text_input",
                    "slot": "main",
                    "props": {"label": "Description", "binding": "description", "required": False},
                    "fulfills": ["VAL-1"],
                },
                {
                    "component_id": "submit_button",
                    "slot": "footer",
                    "props": {"label": "Run Validation", "action": "validate_record"},
                    "fulfills": ["VAL-2"],
                },
                {
                    "component_id": "validation_summary",
                    "slot": "main",
                    "props": {"title": "Validation Result", "binding": "validation_summary"},
                    "fulfills": ["VAL-3"],
                },
            ]
        else:
            components = [
                {
                    "component_id": "file_upload",
                    "slot": "main",
                    "props": {
                        "label": "Invoice File",
                        "binding": "invoice_file",
                        "accept": ["application/pdf", "image/png"],
                    },
                    "fulfills": ["REQ-1"],
                },
                {
                    "component_id": "submit_button",
                    "slot": "footer",
                    "props": {"label": "Run Extraction", "action": "process_invoice"},
                    "fulfills": ["REQ-2"],
                },
                {
                    "component_id": "validation_summary",
                    "slot": "main",
                    "props": {"title": "Validation Summary", "binding": "validation_summary"},
                    "fulfills": ["REQ-3"],
                },
            ]

        return {
            "layout_hints": ["single_column"],
            "components": components,
        }

    def _build_data_flow(self) -> Dict[str, Any]:
        if self._app_type == "TYPE_VALIDATION":
            state = [
                {"name": "record_id", "type": "str", "initial_value": None},
                {"name": "description", "type": "str", "initial_value": ""},
                {"name": "validation_summary", "type": "dict", "initial_value": None},
            ]
            flows = [
                {
                    "step": "run-validation",
                    "trigger": "submit_button.onClick",
                    "source_component": "text_input",
                    "target_component": "validation_summary",
                    "action": "validate_record",
                    "description": "Send the request to the validation service and display the response.",
                    "requirement_refs": ["VAL-2", "VAL-3"],
                }
            ]
        else:
            state = [
                {"name": "invoice_file", "type": "file", "initial_value": None},
                {"name": "validation_summary", "type": "dict", "initial_value": None},
            ]
            flows = [
                {
                    "step": "extract-invoice",
                    "trigger": "submit_button.onClick",
                    "source_component": "file_upload",
                    "target_component": "validation_summary",
                    "action": "extract_and_validate",
                    "description": "Parse the uploaded invoice and update the validation summary.",
                    "requirement_refs": ["REQ-2", "REQ-3"],
                }
            ]

        return {"state": state, "flows": flows}

    def _build_validation(self) -> Dict[str, Any]:
        if self._force_failure:
            return {
                "success": False,
                "errors": [
                    {
                        "code": "validation-failed",
                        "message": "Validation is configured to always fail for testing purposes.",
                        "hint": "Remove the phrase 'force failure' from the prompt to allow success.",
                        "level": "error",
                    }
                ],
            }

        if self._force_retry and self._validation_attempts == 0:
            self._validation_attempts += 1
            return {
                "success": False,
                "errors": [
                    {
                        "code": "retry",
                        "message": "The first validation detected a consistency issue.",
                        "hint": "Retrying once will produce a corrected specification.",
                        "level": "warning",
                    }
                ],
            }

        self._validation_attempts += 1
        return {"success": True, "errors": []}

    @staticmethod
    def _parse_user_prompt(section: str) -> str:
        marker = "User prompt:"
        if marker in section:
            after = section.split(marker, 1)[1]
            if "Return the structured requirements list." in after:
                after = after.split("Return the structured requirements list.", 1)[0]
            return after.strip()
        return section.strip()

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

