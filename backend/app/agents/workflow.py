"""High-level multi-agent orchestration for workflow generation."""

from __future__ import annotations

import re
from typing import Iterable, List

from pydantic import ValidationError

from ..models.workflow import (
    CallWorkflowStep,
    PipelineDefinition,
    PipelineStep,
    SetStateStep,
    UIDefinition,
    UIComponent,
    UIStep,
    WorkflowEndpoint,
    WorkflowInfo,
    WorkflowProvider,
    WorkflowSpecification,
)
from .models import (
    AnalystInsight,
    ArchitectBlueprint,
    PipelineStepPlan,
    UIComponentPlan,
    UIStepPlan,
    ValidationIssue,
    ValidatorReport,
    WorkflowAdapterConfig,
)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


class AnalystAgent:
    """Derives problem framing and success metrics from a natural language brief."""

    def run(self, prompt: str, app_name: str | None = None) -> AnalystInsight:
        invoice_keywords = ("invoice", "??", "??", "??")
        validation_keywords = ("validate", "??", "????", "??")

        if _contains_any(prompt, invoice_keywords):
            inferred_name = "Invoice Validation Assistant"
            persona = "?????"
            actions = ["????????????????", "?????????", "????????????"]
            entities = ["invoice", "vendor", "amount", "due_date", "currency"]
            metrics = ["?????90%??", "1??????????2??????"]
            assumptions = ["???????PDF?????", "???JPY???"]
        elif _contains_any(prompt, validation_keywords):
            inferred_name = "Business Rule Validator"
            persona = "???????"
            actions = ["????ID?????", "??????????", "???????"]
            entities = ["record", "rule", "severity"]
            metrics = ["????????5???", "??????????"]
            assumptions = ["??????Dify????"]
        else:
            inferred_name = "Workflow Automation Assistant"
            persona = "??????"
            actions = ["??????????", "?????????", "???????"]
            entities = ["payload", "result"]
            metrics = ["?????3??????", "?????95%"]
            assumptions = ["??API????????"]

        clean_prompt = re.sub(r"\s+", " ", prompt).strip()

        return AnalystInsight(
            app_name=app_name or inferred_name,
            summary=clean_prompt,
            user_persona=persona,
            primary_actions=actions,
            data_entities=entities,
            success_metrics=metrics,
            assumptions=assumptions,
        )


class ArchitectAgent:
    """Transforms analyst insights into a concrete workflow blueprint."""

    def run(self, insight: AnalystInsight) -> ArchitectBlueprint:
        if "invoice" in insight.summary.lower() or "??" in insight.summary:
            workflows = [
                WorkflowAdapterConfig(
                    id="invoice_validation",
                    name="Invoice Validation Workflow",
                    provider=WorkflowProvider.MOCK,
                    endpoint="${WORKFLOW_PROVIDER_URL}/workflows/invoice-validation",
                    method="POST",
                    description="Run the invoice extraction and validation workflow via Dify or mock provider.",
                )
            ]

            pipeline = [
                PipelineStepPlan(
                    id="capture-inputs",
                    type="set_state",
                    description="Store uploaded invoice file and optional notes in session state.",
                    updates={
                        "invoice_file": "${inputs.invoice_file}",
                        "notes": "${inputs.notes}",
                    },
                ),
                PipelineStepPlan(
                    id="invoke-invoice-validation",
                    type="call_workflow",
                    description="Invoke the invoice validation workflow using uploaded file.",
                    workflow="invoice_validation",
                    input_mapping={"file": "${state.invoice_file}", "notes": "${state.notes}"},
                    save_as="invoice_validation_result",
                ),
            ]

            ui = [
                UIStepPlan(
                    id="upload",
                    title="?????????",
                    description="?????????????????????????",
                    components=[
                        UIComponentPlan(
                            id="invoice_file",
                            type="file_upload",
                            props={
                                "label": "???????",
                                "accept": ["application/pdf", "image/png", "image/jpeg"],
                                "description": "1???????????????",
                            },
                            bindings={"value": "state.invoice_file"},
                        ),
                        UIComponentPlan(
                            id="notes",
                            type="text",
                            props={
                                "label": "????",
                                "multiline": True,
                                "placeholder": "????????????????",
                            },
                            bindings={"value": "state.notes"},
                        ),
                        UIComponentPlan(
                            id="submit",
                            type="button",
                            props={"label": "?????", "variant": "contained"},
                            bindings={"action": "pipeline.invoke-invoice-validation"},
                        ),
                    ],
                ),
                UIStepPlan(
                    id="result",
                    title="????",
                    description="???????????????????",
                    components=[
                        UIComponentPlan(
                            id="summary",
                            type="table",
                            props={"title": "??????"},
                            bindings={"rows": "state.invoice_validation_result.summary"},
                        )
                    ],
                ),
            ]
        else:
            workflows = [
                WorkflowAdapterConfig(
                    id="generic_workflow",
                    name="Generic Workflow",
                    provider=WorkflowProvider.MOCK,
                    endpoint="${WORKFLOW_PROVIDER_URL}/workflows/generic",
                    method="POST",
                    description="Execute a generic workflow for validation or data processing.",
                )
            ]

            pipeline = [
                PipelineStepPlan(
                    id="capture-inputs",
                    type="set_state",
                    description="Store user provided payload in session state.",
                    updates={"payload": "${inputs.payload}"},
                ),
                PipelineStepPlan(
                    id="invoke-generic",
                    type="call_workflow",
                    description="Call the configured workflow with provided payload.",
                    workflow="generic_workflow",
                    input_mapping={"payload": "${state.payload}"},
                    save_as="workflow_result",
                ),
            ]

            ui = [
                UIStepPlan(
                    id="input",
                    title="??",
                    description="??????????????????",
                    components=[
                        UIComponentPlan(
                            id="payload",
                            type="text",
                            props={
                                "label": "?????",
                                "multiline": True,
                                "placeholder": "JSON?????",
                            },
                            bindings={"value": "state.payload"},
                        ),
                        UIComponentPlan(
                            id="submit",
                            type="button",
                            props={"label": "??", "variant": "contained"},
                            bindings={"action": "pipeline.invoke-generic"},
                        ),
                    ],
                ),
                UIStepPlan(
                    id="output",
                    title="??",
                    description="???????????????????",
                    components=[
                        UIComponentPlan(
                            id="result",
                            type="text",
                            props={"label": "??", "variant": "code"},
                            bindings={"value": "state.workflow_result"},
                        )
                    ],
                ),
            ]

        return ArchitectBlueprint(workflows=workflows, pipeline=pipeline, ui=ui)


class SpecialistAgent:
    """Converts the architect blueprint into a concrete workflow specification."""

    def run(self, insight: AnalystInsight, blueprint: ArchitectBlueprint) -> WorkflowSpecification:
        workflow_endpoints: List[WorkflowEndpoint] = [
            WorkflowEndpoint(
                id=item.identifier,
                name=item.name,
                provider=item.provider,
                endpoint=item.endpoint,
                method=item.method,
            )
            for item in blueprint.workflows
        ]

        pipeline_steps = [PipelineStep(self._convert_step(step)) for step in blueprint.pipeline]

        pipeline = PipelineDefinition(entrypoint="main", steps={"main": pipeline_steps})

        ui_steps = [
            UIStep(
                id=step.identifier,
                title=step.title,
                description=step.description,
                layout=step.layout,
                components=[self._convert_component(component) for component in step.components],
            )
            for step in blueprint.ui
        ]

        ui = UIDefinition(steps=ui_steps)

        info = WorkflowInfo(
            name=insight.app_name,
            description=insight.summary,
        )

        return WorkflowSpecification(
            info=info,
            workflows=workflow_endpoints,
            pipeline=pipeline,
            ui=ui,
        )

    def _convert_step(self, plan: PipelineStepPlan) -> CallWorkflowStep | SetStateStep:
        if plan.type == "set_state":
            return SetStateStep(id=plan.identifier, updates=plan.updates or {})

        if plan.type == "call_workflow":
            if not plan.workflow:
                raise ValueError("Call workflow step requires workflow identifier")
            return CallWorkflowStep(
                id=plan.identifier,
                name=plan.description,
                workflow=plan.workflow,
                input_mapping=plan.input_mapping or {},
                save_as=plan.save_as or f"{plan.identifier}_result",
            )

        raise ValueError(f"Unsupported pipeline step type: {plan.type}")

    def _convert_component(self, plan: UIComponentPlan) -> UIComponent:
        return UIComponent(
            id=plan.identifier,
            type=plan.type,
            props=plan.props or {},
            bindings=plan.bindings or {},
        )


class ValidatorAgent:
    """Validates the generated YAML and provides structured issues if any."""

    def run(self, workflow_yaml: str) -> ValidatorReport:
        try:
            WorkflowSpecification.from_yaml(workflow_yaml)
        except ValidationError as exc:
            issues = [
                ValidationIssue(
                    code=err.get("type", "validation_error"),
                    message=err.get("msg", "Invalid workflow specification"),
                    level="error",
                )
                for err in exc.errors()
            ]
            return ValidatorReport(success=False, issues=issues)
        return ValidatorReport(success=True)


__all__ = [
    "AnalystAgent",
    "ArchitectAgent",
    "SpecialistAgent",
    "ValidatorAgent",
]

