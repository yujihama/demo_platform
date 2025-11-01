"""LLM agents for generating workflow.yaml declaratively."""

from __future__ import annotations

from textwrap import dedent
from typing import Any, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from ..services.llm_factory import RetryPolicy
from .base import StructuredLLMAgent
from .models import RequirementsDecompositionResult


class WorkflowAnalysisResult(RequirementsDecompositionResult):
    """Result from Analyst Agent - reusing requirements decomposition structure."""
    pass


class WorkflowArchitectureResult(BaseModel):
    """Result from Architect Agent."""
    
    info_section: Dict[str, Any] = Field(..., description="info section structure")
    workflows_section: Dict[str, Dict[str, str]] = Field(..., description="workflows section with provider configs")
    ui_structure: Dict[str, Any] = Field(..., description="UI section structure outline")
    pipeline_structure: List[Dict[str, Any]] = Field(..., description="Pipeline steps structure outline")
    rationale: str = Field(..., description="Architecture design rationale")


class WorkflowYamlResult(BaseModel):
    """Result from YAML Specialist Agent."""
    
    workflow_yaml: str = Field(..., description="Complete workflow.yaml content as YAML string")


class WorkflowValidationResult(BaseModel):
    """Result from Validator Agent."""
    
    valid: bool = Field(..., description="Whether the YAML is valid")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")


class AnalystAgent(StructuredLLMAgent[WorkflowAnalysisResult]):
    """Analyzes user requirements and breaks them down into structured components."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are a senior product requirements analyst specialized in workflow applications.
                        Your task is to break down user prompts into structured, atomic requirements.
                        
                        Analyze the user's request and identify:
                        - Input requirements: What data or information needs to be collected?
                        - Processing requirements: What operations or transformations need to happen?
                        - Output requirements: What results or actions should be presented?
                        
                        For each requirement, provide:
                        - A unique identifier
                        - A clear title and description
                        - Category (INPUT, PROCESSING, or OUTPUT)
                        - Acceptance criteria describing measurable outcomes
                        
                        Focus on requirements that can be expressed as a declarative workflow,
                        not specific implementation details.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    "User prompt:\n{user_prompt}\n\nAnalyze and return structured requirements.",
                ),
            ]
        )
        super().__init__(
            name="workflow_analyst",
            llm=llm,
            prompt=prompt,
            output_model=WorkflowAnalysisResult,
            retry_policy=retry_policy,
        )

    def run(self, user_prompt: str) -> WorkflowAnalysisResult:
        return self.invoke(user_prompt=user_prompt)


class ArchitectAgent(StructuredLLMAgent[WorkflowArchitectureResult]):
    """Designs the overall structure of workflow.yaml based on requirements."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are a software architect specializing in declarative workflow design.
                        Your task is to design the structure of a workflow.yaml file based on analyzed requirements.
                        
                        workflow.yaml has the following sections:
                        1. info: Application metadata (name, description, version, author)
                        2. workflows: External API endpoints configuration (dify or mock providers)
                        3. ui: Frontend UI definition (optional, with layout and steps)
                        4. pipeline: Backend processing flow (list of steps with components and parameters)
                        
                        Design decisions:
                        - Determine which workflows are needed (typically one for main processing)
                        - Plan UI structure: number of steps, component types needed
                        - Plan pipeline: sequence of operations, data flow between steps
                        - Consider state management: what data needs to persist across steps
                        
                        Provide a high-level structure outline, not the complete YAML yet.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    dedent(
                        """
                        Requirements summary: {summary}
                        
                        Requirements breakdown:
                        {requirements_text}
                        
                        Design the workflow.yaml architecture structure.
                        """
                    ).strip(),
                ),
            ]
        )
        super().__init__(
            name="workflow_architect",
            llm=llm,
            prompt=prompt,
            output_model=WorkflowArchitectureResult,
            retry_policy=retry_policy,
        )

    def run(self, requirements: WorkflowAnalysisResult) -> WorkflowArchitectureResult:
        from .llm_agents import _format_requirements
        
        return self.invoke(
            summary=requirements.summary,
            requirements_text=_format_requirements(requirements),
        )


class YAMLSpecialistAgent(StructuredLLMAgent[WorkflowYamlResult]):
    """Generates the complete workflow.yaml content."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are a YAML specialist expert in generating workflow.yaml files.
                        Your task is to generate a complete, valid workflow.yaml based on the architecture design.
                        
                        workflow.yaml schema:
                        - info: name (str), description (str), version (str), author (str, optional)
                        - workflows: dictionary mapping workflow names to provider configs
                          - provider: "dify" or "mock"
                          - endpoint: API endpoint URL (use environment variables like $DIFY_API_ENDPOINT for dify)
                          - api_key_env: environment variable name for API key (optional)
                        - ui (optional): layout type and steps
                          - layout: "wizard" or "single"
                          - steps: list of step objects with id, title, description, components
                            - components: list with type, id, props
                        - pipeline: list of steps
                          - id: step identifier
                          - component: component name (e.g., "call_workflow", "file_uploader", "for_each")
                          - params: component-specific parameters
                          - condition: optional conditional expression
                          - on_error: optional error handling strategy
                        
                        Generate valid YAML syntax. Use proper indentation. Include all sections.
                        For UI components, use types like: "file_upload", "table", "button", "text_input", "display".
                        """
                    ).strip(),
                ),
                (
                    "human",
                    dedent(
                        """
                        Requirements:
                        {requirements_text}
                        
                        Architecture Design:
                        Info section: {info_section}
                        Workflows section: {workflows_section}
                        UI structure: {ui_structure}
                        Pipeline structure: {pipeline_structure}
                        
                        Generate the complete workflow.yaml YAML content.
                        """
                    ).strip(),
                ),
            ]
        )
        super().__init__(
            name="yaml_specialist",
            llm=llm,
            prompt=prompt,
            output_model=WorkflowYamlResult,
            retry_policy=retry_policy,
        )

    def run(
        self,
        requirements: WorkflowAnalysisResult,
        architecture: WorkflowArchitectureResult,
    ) -> WorkflowYamlResult:
        from .llm_agents import _format_requirements
        
        import json
        return self.invoke(
            requirements_text=_format_requirements(requirements),
            info_section=json.dumps(architecture.info_section, indent=2),
            workflows_section=json.dumps(architecture.workflows_section, indent=2),
            ui_structure=json.dumps(architecture.ui_structure, indent=2),
            pipeline_structure=json.dumps(architecture.pipeline_structure, indent=2),
        )


class ValidatorAgent(StructuredLLMAgent[WorkflowValidationResult]):
    """Validates workflow.yaml and provides feedback for self-correction."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are a workflow.yaml validation specialist.
                        Your task is to validate the generated YAML content and provide feedback.
                        
                        Check for:
                        1. YAML syntax correctness
                        2. Schema compliance: required sections (info, workflows, pipeline) must exist
                        3. Type correctness: provider must be "dify" or "mock", layout must be valid, etc.
                        4. Logical consistency: pipeline steps reference valid workflows, UI components are properly structured
                        5. Completeness: all required fields are present
                        
                        If errors are found, provide clear, actionable error messages.
                        If valid, confirm success and optionally provide improvement suggestions.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    dedent(
                        """
                        Generated workflow.yaml:
                        {workflow_yaml}
                        
                        Previous validation errors (if any):
                        {previous_errors}
                        
                        Validate this YAML and provide feedback.
                        """
                    ).strip(),
                ),
            ]
        )
        super().__init__(
            name="workflow_validator",
            llm=llm,
            prompt=prompt,
            output_model=WorkflowValidationResult,
            retry_policy=retry_policy,
        )

    def run(
        self,
        workflow_yaml: str,
        previous_errors: str | None = None,
    ) -> WorkflowValidationResult:
        return self.invoke(
            workflow_yaml=workflow_yaml,
            previous_errors=previous_errors or "None",
        )
