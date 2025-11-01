"""Concrete structured LLM agents for workflow YAML generation."""

from __future__ import annotations

from textwrap import dedent

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ..services.llm_factory import RetryPolicy
from .base import StructuredLLMAgent
from .models import AnalystResult, ArchitecturePlan, ValidatorFeedback, WorkflowDraft


class AnalystAgent(StructuredLLMAgent[AnalystResult]):
    """Breaks down user intents into structured requirements."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are an analyst for a declarative workflow platform.
                        Analyse the user request and extract structured requirements.
                        - Summarise the primary business goal.
                        - Describe the domain context (target users, data sources, constraints).
                        - Enumerate functional requirements with ids (REQ-1 style), category (input/process/output/validation),
                          detailed description, and measurable acceptance criteria.
                        - List notable risks or unclear assumptions.
                        - Provide example user inputs or payloads if applicable.
                        Always respond in Japanese when appropriate.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    "???????:\n{user_prompt}\n\n????????????????????????",
                ),
            ]
        )
        super().__init__(
            name="analyst",
            llm=llm,
            prompt=prompt,
            output_model=AnalystResult,
            retry_policy=retry_policy,
        )

    def run(self, user_prompt: str) -> AnalystResult:
        return self.invoke(user_prompt=user_prompt)


class ArchitectAgent(StructuredLLMAgent[ArchitecturePlan]):
    """Designs UI wizard and backend pipeline based on analyst findings."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are the architect of a workflow-driven application builder.
                        Using the analyst report, produce an execution plan:
                        - Break the user journey into wizard UI steps with titles, descriptions, and component ids (snake_case).
                        - Outline pipeline steps referencing component outputs and external workflow providers.
                        - Identify external providers (e.g. Dify flows) with id, provider_type, endpoint, and purpose.
                        Use concise Japanese labels. Prefer deterministic naming (lowercase, hyphen or snake_case).
                        """
                    ).strip(),
                ),
                (
                    "human",
                    "??????:\n{analysis}\n\n????????????????????????",
                ),
            ]
        )
        super().__init__(
            name="architect",
            llm=llm,
            prompt=prompt,
            output_model=ArchitecturePlan,
            retry_policy=retry_policy,
        )

    def run(self, analysis: AnalystResult) -> ArchitecturePlan:
        text = _format_analysis(analysis)
        return self.invoke(analysis=text)


class WorkflowSpecialistAgent(StructuredLLMAgent[WorkflowDraft]):
    """Transforms the architecture plan into workflow.yaml content."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You are a workflow YAML specialist. Generate a complete workflow.yaml document.
                        - Honour the provided architecture plan exactly.
                        - Schema: version, info (name, summary, version), workflows (list), pipeline (list), ui (layout, steps).
                        - Use snake_case identifiers. Ensure every identifier matches the plan.
                        - pipeline[].type must be one of: call_workflow, transform, for_each, set_state, branch.
                        - call_workflow steps must reference a provider id defined in workflows.
                        - UI steps layout is "wizard" with ordered steps and component ids.
                        - Include bindings so that UI components consume pipeline outputs when relevant (e.g. results_table binds to pipeline result).
                        Output JSON with fields workflow_yaml (string) and notes (array of short tips).
                        """
                    ).strip(),
                ),
                (
                    "human",
                    "?????????:\n{plan}\n\n???????????YAML??????????",
                ),
            ]
        )
        super().__init__(
            name="workflow_specialist",
            llm=llm,
            prompt=prompt,
            output_model=WorkflowDraft,
            retry_policy=retry_policy,
        )

    def run(self, analysis: AnalystResult, plan: ArchitecturePlan, feedback: str | None = None) -> WorkflowDraft:
        plan_text = _format_plan(analysis, plan, feedback)
        return self.invoke(plan=plan_text)


class WorkflowValidatorAgent(StructuredLLMAgent[ValidatorFeedback]):
    """Summarises validation issues and produces human feedback."""

    def __init__(self, llm: BaseChatModel, retry_policy: RetryPolicy) -> None:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    dedent(
                        """
                        You review workflow YAML validation errors and craft remediation guidance for the specialist agent.
                        - When error list is empty, set is_valid=true and offer deployment tips.
                        - Otherwise set is_valid=false, summarise each error in Japanese, and propose concrete fixes referencing sections (e.g., workflows[0].id).
                        Respond using structured JSON fields.
                        """
                    ).strip(),
                ),
                (
                    "human",
                    "????:\n{errors}\n\n???YAML????:\n{metadata}\n",
                ),
            ]
        )
        super().__init__(
            name="workflow_validator_feedback",
            llm=llm,
            prompt=prompt,
            output_model=ValidatorFeedback,
            retry_policy=retry_policy,
        )

    def run(self, errors: str, metadata: str) -> ValidatorFeedback:
        return self.invoke(errors=errors, metadata=metadata)


def _format_analysis(analysis: AnalystResult) -> str:
    requirement_lines = []
    for req in analysis.requirements:
        ac = " / ".join(req.acceptance_criteria) if req.acceptance_criteria else "(????????)"
        requirement_lines.append(f"- {req.id} [{req.category}] {req.title}: {req.detail} | AC: {ac}")
    risks = "\n".join(f"- {risk}" for risk in analysis.risks) or "- ?????"
    inputs = "\n".join(f"- {example}" for example in analysis.sample_inputs) or "- ????"
    return (
        f"Primary Goal: {analysis.primary_goal}\n"
        f"Domain Context: {analysis.domain_context}\n"
        f"Requirements:\n{chr(10).join(requirement_lines)}\n"
        f"Risks:\n{risks}\n"
        f"Sample Inputs:\n{inputs}"
    )


def _format_plan(analysis: AnalystResult, plan: ArchitecturePlan, feedback: str | None) -> str:
    steps = []
    for step in plan.ui_steps:
        components = ", ".join(step.components) or "components not specified"
        steps.append(f"- {step.id}: {step.title} ({components}) -> next: {step.success_transition or 'end'}")
    pipeline_steps = []
    for step in plan.pipeline:
        pipeline_steps.append(
            f"- {step.id} [{step.type}] provider={step.uses_provider or 'n/a'} inputs={', '.join(step.inputs) or '-'} outputs={', '.join(step.outputs) or '-'}"
        )
    workflow_refs = []
    for ref in plan.workflows:
        workflow_refs.append(f"- {ref.id} ({ref.provider_type}) {ref.endpoint}: {ref.description}")
    formatted_feedback = feedback or "(?????????????????????)"
    return (
        f"User Goal: {analysis.primary_goal}\n"
        f"UI Steps:\n{chr(10).join(steps)}\n"
        f"Pipeline Steps:\n{chr(10).join(pipeline_steps)}\n"
        f"Workflows:\n{chr(10).join(workflow_refs)}\n"
        f"Previous Feedback:\n{formatted_feedback}"
    )


