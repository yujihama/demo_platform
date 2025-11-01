"""Service coordinating the declarative workflow generation pipeline."""

from __future__ import annotations

import time

from fastapi import HTTPException, status

from ..agents.workflow import AnalystAgent, ArchitectAgent, SpecialistAgent, ValidatorAgent
from ..models import (
    AgentMessage,
    AgentRole,
    WorkflowGenerationRequest,
    WorkflowGenerationResponse,
)


class WorkflowGenerationService:
    """Coordinates the multi-agent flow to produce workflow specifications."""

    def __init__(self) -> None:
        self._analyst = AnalystAgent()
        self._architect = ArchitectAgent()
        self._specialist = SpecialistAgent()
        self._validator = ValidatorAgent()

    def generate(self, request: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
        start = time.perf_counter()
        messages: list[AgentMessage] = []

        insight = self._analyst.run(request.prompt, request.app_name)
        messages.append(
            AgentMessage(
                role=AgentRole.ANALYST,
                title="????",
                content=f"????: {insight.app_name}\n??????: {insight.user_persona}\n???????: {', '.join(insight.primary_actions)}",
                metadata={
                    "success_metrics": insight.success_metrics,
                    "assumptions": insight.assumptions,
                },
            )
        )

        blueprint = self._architect.run(insight)
        messages.append(
            AgentMessage(
                role=AgentRole.ARCHITECT,
                title="?????????",
                content=f"???????: {len(blueprint.workflows)}\n???????????: {len(blueprint.pipeline)}",
                metadata={
                    "workflows": [workflow.identifier for workflow in blueprint.workflows],
                    "ui_steps": [step.identifier for step in blueprint.ui],
                },
            )
        )

        workflow = self._specialist.run(insight, blueprint)
        workflow_yaml = workflow.to_yaml()
        messages.append(
            AgentMessage(
                role=AgentRole.SPECIALIST,
                title="YAML??",
                content="???workflow.yaml????????",
            )
        )

        validation = self._validator.run(workflow_yaml)
        if not validation.success:
            messages.append(
                AgentMessage(
                    role=AgentRole.VALIDATOR,
                    title="??????",
                    content="workflow.yaml?????????????????",
                    success=False,
                    metadata={"issues": [issue.model_dump() for issue in validation.issues]},
                )
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "workflow.yaml ??????????",
                    "issues": [issue.model_dump() for issue in validation.issues],
                },
            )

        messages.append(
            AgentMessage(
                role=AgentRole.VALIDATOR,
                title="??????",
                content="workflow.yaml????????????????",
            )
        )

        duration_ms = int((time.perf_counter() - start) * 1000)

        return WorkflowGenerationResponse(
            workflow=workflow,
            workflow_yaml=workflow_yaml,
            messages=messages,
            retries=0,
            duration_ms=duration_ms,
        )


workflow_generation_service = WorkflowGenerationService()

