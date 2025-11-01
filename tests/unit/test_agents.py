from __future__ import annotations

from typing import Any, List

from backend.app.agents import (
    AppTypeClassificationAgent,
    ComponentSelectionAgent,
    DataFlowDesignAgent,
    RequirementsDecompositionAgent,
    SpecificationValidatorAgent,
)
from backend.app.agents.models import (
    AppTypeClassificationResult,
    ComponentSelectionResult,
    DataFlowDesignResult,
    RequirementsDecompositionResult,
)
from backend.app.services.llm_factory import RetryPolicy
from backend.app.services.ui_catalog import load_ui_catalog


class FakeLLM:
    """Simple fake LLM that returns predetermined structured outputs."""

    def __init__(self, responses: List[dict[str, Any]]) -> None:
        self._responses = responses

    def with_structured_output(self, output_model: Any) -> Any:  # noqa: ANN401
        outer = self

        class _FakeRunnable:
            def invoke(self, _: Any) -> Any:  # noqa: ANN401
                if not outer._responses:
                    raise AssertionError("No more mock responses available")
                payload = outer._responses.pop(0)
                return output_model(**payload)

        return _FakeRunnable()


def test_requirements_decomposition_agent_returns_model() -> None:
    fake_llm = FakeLLM(
        [
            {
                "summary": "Automated validation workflow",
                "primary_goal": "Validate records quickly",
                "requirements": [
                    {
                        "id": "VAL-1",
                        "category": "INPUT",
                        "title": "Capture record",
                        "description": "Allow operators to capture record IDs",
                        "acceptance_criteria": ["Supports multiple records"],
                    }
                ],
            }
        ]
    )

    agent = RequirementsDecompositionAgent(fake_llm, RetryPolicy())
    result = agent.run("Validate the submitted record against business rules")

    assert isinstance(result, RequirementsDecompositionResult)
    assert result.summary == "Automated validation workflow"
    assert result.requirements[0].id == "VAL-1"


def test_app_type_classification_agent_uses_structured_output() -> None:
    fake_llm = FakeLLM(
        [
            {
                "app_type": "TYPE_VALIDATION",
                "confidence": 0.9,
                "rationale": "Keyword match",
                "recommended_template": "validation-workflow-basic",
                "supporting_requirements": ["VAL-1"],
            }
        ]
    )
    agent = AppTypeClassificationAgent(fake_llm, RetryPolicy())
    requirements = RequirementsDecompositionResult(
        summary="Validation workflow",
        primary_goal="Ensure data quality",
        requirements=[],
    )

    result = agent.run(requirements)

    assert isinstance(result, AppTypeClassificationResult)
    assert result.app_type == "TYPE_VALIDATION"
    assert result.recommended_template == "validation-workflow-basic"


def test_component_selection_agent_returns_components() -> None:
    fake_llm = FakeLLM(
        [
            {
                "layout_hints": ["single_column"],
                "components": [
                    {
                        "component_id": "text_input",
                        "slot": "main",
                        "props": {"label": "Record ID", "binding": "record_id", "required": True},
                        "fulfills": ["VAL-1"],
                    }
                ],
            }
        ]
    )
    catalog = load_ui_catalog()
    agent = ComponentSelectionAgent(fake_llm, RetryPolicy())

    requirements = RequirementsDecompositionResult(
        summary="Validation workflow",
        primary_goal="Ensure data quality",
        requirements=[],
    )
    classification = AppTypeClassificationResult(
        app_type="TYPE_VALIDATION",
        confidence=0.9,
        rationale="Keyword match",
        recommended_template="validation-workflow-basic",
        supporting_requirements=["VAL-1"],
    )

    result = agent.run(requirements, classification, catalog)

    assert isinstance(result, ComponentSelectionResult)
    assert result.components[0].component_id == "text_input"


def test_data_flow_design_agent_returns_flow() -> None:
    fake_llm = FakeLLM(
        [
            {
                "state": [{"name": "record_id", "type": "str", "initial_value": None}],
                "flows": [
                    {
                        "step": "validate",
                        "trigger": "submit_button.onClick",
                        "source_component": "text_input",
                        "target_component": "validation_summary",
                        "action": "validate_record",
                        "description": "Validate the record",
                        "requirement_refs": ["VAL-1"],
                    }
                ],
            }
        ]
    )
    agent = DataFlowDesignAgent(fake_llm, RetryPolicy())

    requirements = RequirementsDecompositionResult(
        summary="Validation workflow",
        primary_goal="Ensure data quality",
        requirements=[],
    )
    classification = AppTypeClassificationResult(
        app_type="TYPE_VALIDATION",
        confidence=0.9,
        rationale="Keyword match",
        recommended_template="validation-workflow-basic",
        supporting_requirements=["VAL-1"],
    )
    components = ComponentSelectionResult(layout_hints=[], components=[])

    result = agent.run(requirements, classification, components)

    assert isinstance(result, DataFlowDesignResult)
    assert result.flows[0].step == "validate"


def test_validator_agent_returns_success() -> None:
    fake_llm = FakeLLM(
        [
            {
                "success": True,
                "errors": [],
            }
        ]
    )
    catalog = load_ui_catalog()
    agent = SpecificationValidatorAgent(fake_llm, RetryPolicy())

    requirements = RequirementsDecompositionResult(summary="", primary_goal="", requirements=[])
    components = ComponentSelectionResult(layout_hints=[], components=[])
    flows = DataFlowDesignResult(state=[], flows=[])

    result = agent.run(requirements, components, flows, catalog)

    assert result.success is True
    assert result.errors == []


def test_validator_agent_bubbles_errors() -> None:
    fake_llm = FakeLLM(
        [
            {
                "success": False,
                "errors": [
                    {
                        "code": "missing-component",
                        "message": "Component is not in catalog",
                        "hint": "Ensure the component ID exists",
                        "level": "error",
                    }
                ],
            }
        ]
    )
    catalog = load_ui_catalog()
    agent = SpecificationValidatorAgent(fake_llm, RetryPolicy())

    requirements = RequirementsDecompositionResult(summary="", primary_goal="", requirements=[])
    components = ComponentSelectionResult(layout_hints=[], components=[])
    flows = DataFlowDesignResult(state=[], flows=[])

    result = agent.run(requirements, components, flows, catalog)

    assert result.success is False
    assert result.errors[0].code == "missing-component"
