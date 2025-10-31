"""Concrete structured LLM agents used in the generation pipeline."""

from __future__ import annotations

from textwrap import dedent

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ..services.llm_factory import RetryPolicy
from ..services.ui_catalog import UIPartsCatalog
from .base import StructuredLLMAgent
from .models import (
    AppTypeClassificationResult,
    ComponentPlacement,
    ComponentSelectionResult,
    DataFlowDesignResult,
    RequirementsDecompositionResult,
    ValidationResult,
)


class RequirementsDecompositionAgent(StructuredLLMAgent[RequirementsDecompositionResult]):
    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are a senior product requirements analyst. Break down user prompts into numbered, atomic requirements.
                        - Create concise titles and detailed descriptions.
                        - Categorise each requirement as INPUT, PROCESSING, or OUTPUT.
                        - Provide acceptance criteria bullet points describing measurable outcomes.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    "User prompt:\n{user_prompt}\n\nReturn the structured requirements list.",
                ),
            ]
        )
        super().__init__(
            name="requirements_decomposition",
            llm=llm,
            prompt=prompt,
            output_model=RequirementsDecompositionResult,
            retry_policy=retry_policy,
        )

    def run(self, user_prompt: str) -> RequirementsDecompositionResult:
        return self.invoke(user_prompt=user_prompt)


class AppTypeClassificationAgent(StructuredLLMAgent[AppTypeClassificationResult]):
    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You classify applications for an AI code generation platform.
                        Choose the best matching type from: TYPE_CRUD, TYPE_DOCUMENT_PROCESSOR, TYPE_VALIDATION, TYPE_ANALYTICS, TYPE_CHATBOT.
                        Explain the rationale and reference supporting requirement identifiers.
                        Recommend a template name such as `document-processor-basic` or `validation-workflow-basic`.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    "Summary:{summary}\n\nRequirements:\n{requirements_text}",
                ),
            ]
        )
        super().__init__(
            name="app_type_classification",
            llm=llm,
            prompt=prompt,
            output_model=AppTypeClassificationResult,
            retry_policy=retry_policy,
        )

    def run(self, requirements: RequirementsDecompositionResult) -> AppTypeClassificationResult:
        return self.invoke(
            summary=requirements.summary,
            requirements_text=_format_requirements(requirements),
        )


class ComponentSelectionAgent(StructuredLLMAgent[ComponentSelectionResult]):
    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You select UI components for a low-code platform using a predefined component catalogue.
                        - Use only components listed in the catalogue.
                        - Assign each component to a slot such as 'hero', 'sidebar', 'main', or 'footer'.
                        - Provide props with serialisable values.
                        - Map each component to requirement identifiers it fulfills.
                        Provide at least one component fulfilling every requirement.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    dedent(
                        """
                        Application type: {app_type}
                        Recommended template: {template}

                        Component catalogue:
                        {catalogue}

                        Requirements:
                        {requirements_text}

                        Validator feedback (if any):
                        {feedback}
                        """
                    ).strip(),
                ),
            ]
        )
        super().__init__(
            name="component_selection",
            llm=llm,
            prompt=prompt,
            output_model=ComponentSelectionResult,
            retry_policy=retry_policy,
        )

    def run(
        self,
        requirements: RequirementsDecompositionResult,
        classification: AppTypeClassificationResult,
        catalog: UIPartsCatalog,
        feedback: str | None = None,
    ) -> ComponentSelectionResult:
        return self.invoke(
            app_type=classification.app_type,
            template=classification.recommended_template,
            catalogue=_summarise_catalog(catalog, classification.app_type),
            requirements_text=_format_requirements(requirements),
            feedback=feedback or "??",
        )


class DataFlowDesignAgent(StructuredLLMAgent[DataFlowDesignResult]):
    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You design deterministic data flows between selected UI components.
                        - Connect components respecting triggers and actions.
                        - Define state variables with snake_case names.
                        - Ensure each flow references requirement identifiers that it satisfies.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    dedent(
                        """
                        Application type: {app_type}
                        Requirements:
                        {requirements_text}

                        Selected components:
                        {components_text}
                        """
                    ).strip(),
                ),
            ]
        )
        super().__init__(
            name="data_flow_design",
            llm=llm,
            prompt=prompt,
            output_model=DataFlowDesignResult,
            retry_policy=retry_policy,
        )

    def run(
        self,
        requirements: RequirementsDecompositionResult,
        classification: AppTypeClassificationResult,
        components: ComponentSelectionResult,
    ) -> DataFlowDesignResult:
        return self.invoke(
            app_type=classification.app_type,
            requirements_text=_format_requirements(requirements),
            components_text=_format_components(components),
        )


class SpecificationValidatorAgent(StructuredLLMAgent[ValidationResult]):
    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You validate specifications for an AI-generated application.
                        - Ensure every component exists in the supplied catalogue.
                        - Verify component props align with the catalogue definitions.
                        - Ensure data flows reference existing components and state variables.
                        - Detect circular dependencies between flows.
                        - Confirm every requirement identifier is fulfilled by at least one component or data flow.
                        Return success=true when the specification passes all checks; otherwise list detailed issues with hints.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    dedent(
                        """
                        Catalogue:
                        {catalogue}

                        Requirements:
                        {requirements_text}

                        Components:
                        {components_text}

                        Data flows:
                        {flows_text}
                        """
                    ).strip(),
                ),
            ]
        )
        super().__init__(
            name="validator",
            llm=llm,
            prompt=prompt,
            output_model=ValidationResult,
            retry_policy=retry_policy,
        )

    def run(
        self,
        requirements: RequirementsDecompositionResult,
        components: ComponentSelectionResult,
        flows: DataFlowDesignResult,
        catalog: UIPartsCatalog,
    ) -> ValidationResult:
        return self.invoke(
            catalogue=_summarise_catalog(catalog),
            requirements_text=_format_requirements(requirements),
            components_text=_format_components(components),
            flows_text=_format_flows(flows),
        )


def _format_requirements(requirements: RequirementsDecompositionResult) -> str:
    lines = [f"- {item.id} ({item.category}): {item.title} - {item.description}" for item in requirements.requirements]
    return "\n".join(lines)


def _format_components(selection: ComponentSelectionResult) -> str:
    lines: list[str] = []
    for component in selection.components:
        prop_str = ", ".join(f"{key}={value}" for key, value in component.props.items()) or "no props"
        fulfills = ", ".join(component.fulfills) or "none"
        lines.append(f"- {component.component_id} @ {component.slot} ({prop_str}) -> {fulfills}")
    return "\n".join(lines)


def _format_flows(flows: DataFlowDesignResult) -> str:
    lines: list[str] = []
    for edge in flows.flows:
        refs = ", ".join(edge.requirement_refs) or "none"
        lines.append(
            f"- {edge.step}: {edge.source_component} --[{edge.trigger}/{edge.action}]--> {edge.target_component} ({refs})"
        )
    state_lines = [f"state {var.name}: {var.type} (init={var.initial_value})" for var in flows.state]
    return "\n".join(state_lines + lines)


def _summarise_catalog(catalog: UIPartsCatalog, app_type: str | None = None) -> str:
    lines: list[str] = []
    for definition in catalog.components.values():
        if app_type and not definition.supports_app_type(app_type):
            continue
        props = ", ".join(f"{name}:{prop.type}{'!' if prop.required else ''}" for name, prop in definition.props.items())
        applicable = ", ".join(definition.applicable_app_types) or "all"
        lines.append(f"- {definition.id} ({definition.category}, {applicable}) props[{props}]")
    return "\n".join(lines)

