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
from backend.app.services.llm_factory import MockStructuredChatModel, RetryPolicy
from backend.app.services.ui_catalog import load_ui_catalog


def _default_prompt() -> str:
    return "請求書からデータを抽出し検証するワークフローを作成して"


def test_requirements_decomposition_agent_returns_model() -> None:
    llm = MockStructuredChatModel()
    agent = RequirementsDecompositionAgent(llm, RetryPolicy())

    result = agent.run(_default_prompt())

    assert isinstance(result, RequirementsDecompositionResult)
    assert result.summary.startswith("Automated document processing workflow")
    assert len(result.requirements) >= 1


def test_app_type_classification_agent_uses_structured_output() -> None:
    llm = MockStructuredChatModel()
    policy = RetryPolicy()
    requirements = RequirementsDecompositionAgent(llm, policy).run(_default_prompt())

    agent = AppTypeClassificationAgent(llm, policy)
    result = agent.run(requirements)

    assert isinstance(result, AppTypeClassificationResult)
    assert result.app_type in {"TYPE_DOCUMENT_PROCESSOR", "TYPE_VALIDATION"}
    assert result.recommended_template is not None


def test_component_selection_agent_returns_components() -> None:
    llm = MockStructuredChatModel()
    policy = RetryPolicy()
    requirements = RequirementsDecompositionAgent(llm, policy).run(_default_prompt())
    classification = AppTypeClassificationAgent(llm, policy).run(requirements)

    catalog = load_ui_catalog()
    agent = ComponentSelectionAgent(llm, policy)
    result = agent.run(requirements, classification, catalog)

    assert isinstance(result, ComponentSelectionResult)
    assert len(result.components) > 0


def test_data_flow_design_agent_returns_flow() -> None:
    llm = MockStructuredChatModel()
    policy = RetryPolicy()
    requirements = RequirementsDecompositionAgent(llm, policy).run(_default_prompt())
    classification = AppTypeClassificationAgent(llm, policy).run(requirements)
    components = ComponentSelectionAgent(llm, policy).run(requirements, classification, load_ui_catalog())

    agent = DataFlowDesignAgent(llm, policy)
    result = agent.run(requirements, classification, components)

    assert isinstance(result, DataFlowDesignResult)
    assert len(result.flows) > 0


def test_validator_agent_returns_success() -> None:
    llm = MockStructuredChatModel()
    policy = RetryPolicy()
    requirements = RequirementsDecompositionAgent(llm, policy).run(_default_prompt())
    classification = AppTypeClassificationAgent(llm, policy).run(requirements)
    components = ComponentSelectionAgent(llm, policy).run(requirements, classification, load_ui_catalog())
    flows = DataFlowDesignAgent(llm, policy).run(requirements, classification, components)

    agent = SpecificationValidatorAgent(llm, policy)
    result = agent.run(requirements, components, flows, load_ui_catalog())

    assert result.success is True
    assert result.errors == []


def test_validator_agent_bubbles_errors() -> None:
    failing_llm = MockStructuredChatModel()
    failing_llm._force_failure = True  # type: ignore[attr-defined]
    policy = RetryPolicy()
    requirements = RequirementsDecompositionAgent(failing_llm, policy).run("検証に失敗するワークフローを生成して force failure")
    classification = AppTypeClassificationAgent(failing_llm, policy).run(requirements)
    components = ComponentSelectionAgent(failing_llm, policy).run(requirements, classification, load_ui_catalog())
    flows = DataFlowDesignAgent(failing_llm, policy).run(requirements, classification, components)

    agent = SpecificationValidatorAgent(failing_llm, policy)
    result = agent.run(requirements, components, flows, load_ui_catalog())

    assert result.success is False
    assert len(result.errors) >= 1
