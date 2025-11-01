"""Declarative workflow generation pipeline orchestrating LLM agents and packaging."""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence
from uuid import uuid4

from fastapi import BackgroundTasks

from ..agents import (
    AnalystAgent,
    AnalystResult,
    ArchitectAgent,
    ArchitecturePlan,
    WorkflowSpecialistAgent,
    WorkflowValidatorAgent,
)
from ..config import ConfigManager, config_manager
from ..models.generation import GenerationJob, GenerationRequest, JobStatus, StepStatus
from ..workflow import WorkflowDocument, WorkflowSerializer, WorkflowValidationError, WorkflowValidator
from .jobs import JobRegistry, job_registry
from .llm_factory import RetryPolicy, llm_factory
from .packaging import PackagingService

logger = logging.getLogger(__name__)


WORKFLOW_STEP_DEFINITIONS: Sequence[tuple[str, str]] = (
    ("requirements", "????"),
    ("analysis", "????"),
    ("architecture", "?????????"),
    ("yaml_generation", "YAML??"),
    ("validation", "??????"),
    ("packaging", "???????"),
)

MOCK_STEP_DEFINITIONS: Sequence[tuple[str, str]] = (
    ("requirements", "????"),
    ("mock_workflow", "???workflow??"),
    ("validation", "??????"),
    ("packaging", "???????"),
)

MAX_VALIDATION_ATTEMPTS = 3


@dataclass
class WorkflowArtifacts:
    document: WorkflowDocument
    yaml_text: str
    metadata: Dict[str, Any]
    notes: List[str]


class GenerationPipeline:
    """Coordinates LLM agents, validation, and packaging for workflow.yaml generation."""

    def __init__(
        self,
        config_manager: ConfigManager = config_manager,
        jobs: JobRegistry = job_registry,
        working_root: Path = Path("generated"),
    ) -> None:
        self._config_manager = config_manager
        self._jobs = jobs
        self._llm_factory = llm_factory
        features = self._config_manager.features
        self._packaging = PackagingService(Path(features.generation.output_root))
        self._working_root = working_root
        self._working_root.mkdir(parents=True, exist_ok=True)
        self._workflow_validator = WorkflowValidator()
        self._mock_workflow_root = Path("mock/workflows")

    # ------------------------------------------------------------------
    def enqueue(self, request: GenerationRequest, background_tasks: BackgroundTasks) -> GenerationJob:
        job_id = str(uuid4())
        use_mock = self._resolve_use_mock(request)
        step_definitions = self._select_steps(use_mock)
        job = self._jobs.create_job(job_id, request, step_definitions)
        background_tasks.add_task(self._run_job, job.job_id, request, use_mock)
        logger.info("Enqueued generation job %s", job_id)
        return job

    # ------------------------------------------------------------------
    def run_sync(
        self,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> GenerationJob:
        job_id = str(uuid4())
        use_mock = self._resolve_use_mock(request)
        step_definitions = self._select_steps(use_mock)
        job = self._jobs.create_job(job_id, request, step_definitions)
        logger.info("Running generation job %s synchronously", job_id)
        if progress_callback:
            self._notify(job_id, progress_callback)
        self._run_job(job_id, request, use_mock, progress_callback=progress_callback)
        final_job = self._jobs.get(job_id)
        if final_job is None:
            raise RuntimeError("Job finished without persisted state")
        return final_job

    # ------------------------------------------------------------------
    def _run_job(
        self,
        job_id: str,
        request: GenerationRequest,
        use_mock: bool,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> None:
        workspace = self._working_root / job_id
        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        prompt = (request.requirements_prompt or request.description or "").strip()
        if not prompt:
            self._jobs.fail(job_id, "?????????????????")
            self._notify(job_id, progress_callback)
            return

        try:
            self._jobs.update_status(
                job_id,
                step_id="requirements",
                job_status=JobStatus.RECEIVED,
                step_status=StepStatus.COMPLETED,
                message="?????????",
            )
            self._notify(job_id, progress_callback)

            if use_mock:
                artifacts = self._run_mock_pipeline(job_id, request, workspace, progress_callback)
            else:
                artifacts = self._run_llm_pipeline(job_id, prompt, request, workspace, progress_callback)

            job_snapshot = self._jobs.get(job_id)
            if job_snapshot is None:
                raise RuntimeError("Job snapshot missing during packaging")

            metadata = dict(artifacts.metadata)
            metadata["workflow_yaml"] = artifacts.yaml_text

            self._jobs.update_status(
                job_id,
                step_id="packaging",
                job_status=JobStatus.PACKAGING,
                step_status=StepStatus.RUNNING,
                message="?????????????",
            )
            self._notify(job_id, progress_callback)

            zip_path = self._packaging.package(job_snapshot, artifacts.yaml_text, metadata, artifacts.notes)

            download_url = f"/api/generate/{job_id}/download"
            self._jobs.complete(job_id, download_url, metadata, str(zip_path))
            self._notify(job_id, progress_callback)
            logger.info("Generation job %s completed", job_id)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Generation job %s failed", job_id)
            self._jobs.fail(job_id, str(exc))
            self._notify(job_id, progress_callback)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    # ------------------------------------------------------------------
    def _run_mock_pipeline(
        self,
        job_id: str,
        request: GenerationRequest,
        workspace: Path,
        progress_callback: Callable[[GenerationJob], None] | None,
    ) -> WorkflowArtifacts:
        self._jobs.update_status(
            job_id,
            step_id="mock_workflow",
            job_status=JobStatus.ANALYSING,
            step_status=StepStatus.RUNNING,
            message="???workflow?????????",
        )
        self._notify(job_id, progress_callback)

        mock_path = self._mock_workflow_root / f"{request.mock_spec_id}.yaml"
        if not mock_path.exists():
            raise FileNotFoundError(f"???workflow????????: {mock_path}")

        yaml_text = mock_path.read_text(encoding="utf-8")
        document, errors = self._workflow_validator.validate_yaml(yaml_text)
        if errors:
            error_text = self._format_validation_errors(errors)
            raise ValueError(f"???workflow??????????????:\n{error_text}")

        normalised_yaml = WorkflowSerializer.to_yaml(document)
        self._write_text(workspace / "workflow.mock.yaml", normalised_yaml)

        self._jobs.update_status(
            job_id,
            step_id="mock_workflow",
            job_status=JobStatus.ANALYSING,
            step_status=StepStatus.COMPLETED,
            message="???workflow????????",
        )
        self._jobs.update_status(
            job_id,
            step_id="validation",
            job_status=JobStatus.VALIDATING,
            step_status=StepStatus.COMPLETED,
            message="?????????????",
        )
        self._notify(job_id, progress_callback)

        notes = [f"????????? '{request.mock_spec_id}' ????????"]
        metadata = {
            "mode": "mock",
            "mock_spec_id": request.mock_spec_id,
            "request": request.model_dump(),
            "notes": notes,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        return WorkflowArtifacts(document=document, yaml_text=normalised_yaml, metadata=metadata, notes=notes)

    # ------------------------------------------------------------------
    def _run_llm_pipeline(
        self,
        job_id: str,
        prompt: str,
        request: GenerationRequest,
        workspace: Path,
        progress_callback: Callable[[GenerationJob], None] | None,
    ) -> WorkflowArtifacts:
        llm = self._llm_factory.create_chat_model()
        retry_policy: RetryPolicy = self._llm_factory.get_retry_policy()

        analyst = AnalystAgent(llm, retry_policy)
        architect = ArchitectAgent(llm, retry_policy)
        specialist = WorkflowSpecialistAgent(llm, retry_policy)
        validator_feedback_agent = WorkflowValidatorAgent(llm, retry_policy)

        self._jobs.update_status(
            job_id,
            step_id="analysis",
            job_status=JobStatus.ANALYSING,
            step_status=StepStatus.RUNNING,
            message="LLM???????????",
        )
        self._notify(job_id, progress_callback)
        analysis = analyst.run(prompt)
        self._write_json(workspace / "analysis.json", analysis.model_dump(mode="json"))
        self._jobs.update_status(
            job_id,
            step_id="analysis",
            job_status=JobStatus.ANALYSING,
            step_status=StepStatus.COMPLETED,
            message="???????????",
        )
        self._notify(job_id, progress_callback)

        self._jobs.update_status(
            job_id,
            step_id="architecture",
            job_status=JobStatus.ARCHITECTING,
            step_status=StepStatus.RUNNING,
            message="LLM??????????????????",
        )
        self._notify(job_id, progress_callback)
        plan = architect.run(analysis)
        self._write_json(workspace / "architecture_plan.json", plan.model_dump(mode="json"))
        self._jobs.update_status(
            job_id,
            step_id="architecture",
            job_status=JobStatus.ARCHITECTING,
            step_status=StepStatus.COMPLETED,
            message="????????????????",
        )
        self._notify(job_id, progress_callback)

        notes: List[str] = []
        attempt_records: List[Dict[str, Any]] = []
        feedback_for_specialist: str | None = None
        final_document: WorkflowDocument | None = None
        final_yaml: str | None = None

        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            attempt_message = f"workflow.yaml ???????? (?? {attempt}/{MAX_VALIDATION_ATTEMPTS})"
            self._jobs.update_status(
                job_id,
                step_id="yaml_generation",
                job_status=JobStatus.WORKFLOW_GENERATING,
                step_status=StepStatus.RUNNING,
                message=attempt_message,
                log_entry=feedback_for_specialist,
            )
            self._notify(job_id, progress_callback)

            draft = specialist.run(analysis, plan, feedback_for_specialist)
            yaml_text = draft.workflow_yaml.strip()
            if not yaml_text.endswith("\n"):
                yaml_text += "\n"
            self._write_text(workspace / f"workflow_attempt_{attempt}.yaml", yaml_text)

            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.VALIDATING,
                step_status=StepStatus.RUNNING,
                message=f"?????????? (?? {attempt})",
            )
            self._notify(job_id, progress_callback)

            document, errors = self._workflow_validator.validate_yaml(yaml_text)
            attempt_records.append(
                {
                    "attempt": attempt,
                    "errors": [err.__dict__ for err in errors],
                    "feedback": feedback_for_specialist,
                    "notes": draft.notes,
                }
            )

            if errors:
                error_text = self._format_validation_errors(errors)
                self._write_text(workspace / f"validation_errors_attempt_{attempt}.log", error_text)
                metadata_summary = self._build_metadata_summary(analysis, plan)
                feedback = validator_feedback_agent.run(errors=error_text, metadata=metadata_summary)
                feedback_for_specialist = "\n".join(feedback.suggestions or []) or error_text
                notes.extend(draft.notes)
                self._jobs.update_status(
                    job_id,
                    step_id="validation",
                    job_status=JobStatus.VALIDATING,
                    step_status=StepStatus.RUNNING,
                    message=f"????????????????? (?? {attempt})????????",
                    log_entry=error_text,
                )
                self._notify(job_id, progress_callback)
                if attempt >= MAX_VALIDATION_ATTEMPTS:
                    raise RuntimeError(f"workflow.yaml ??????????: {error_text}")
                continue

            final_document = document
            final_yaml = WorkflowSerializer.to_yaml(document)
            self._write_text(workspace / "workflow.final.yaml", final_yaml)
            notes.extend(draft.notes)

            validator_summary = validator_feedback_agent.run(errors="[]", metadata=self._build_metadata_summary(analysis, plan))
            notes.extend(validator_summary.suggestions)

            self._jobs.update_status(
                job_id,
                step_id="yaml_generation",
                job_status=JobStatus.WORKFLOW_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="workflow.yaml ??????????",
            )
            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.VALIDATING,
                step_status=StepStatus.COMPLETED,
                message="?????????????",
            )
            self._notify(job_id, progress_callback)
            break
        else:
            raise RuntimeError("workflow.yaml ?????????? (?????????)")

        if final_document is None or final_yaml is None:
            raise RuntimeError("workflow.yaml ????????????????")

        metadata = {
            "mode": "llm",
            "request": request.model_dump(),
            "analysis": analysis.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "attempts": attempt_records,
            "notes": notes,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

        return WorkflowArtifacts(document=final_document, yaml_text=final_yaml, metadata=metadata, notes=notes)

    # ------------------------------------------------------------------
    def _format_validation_errors(self, errors: Iterable[WorkflowValidationError]) -> str:
        lines = []
        for err in errors:
            lines.append(f"- path={err.path} code={err.code} message={err.message}")
        return "\n".join(lines)

    def _build_metadata_summary(self, analysis: AnalystResult, plan: ArchitecturePlan) -> str:
        ui_steps = ", ".join(f"{step.id}:{step.title}" for step in plan.ui_steps) or "(none)"
        pipeline_steps = ", ".join(f"{step.id}/{step.type}" for step in plan.pipeline) or "(none)"
        workflows = ", ".join(f"{wf.id}->{wf.provider_type}" for wf in plan.workflows) or "(none)"
        return (
            f"Goal: {analysis.primary_goal}\n"
            f"UI Steps: {ui_steps}\n"
            f"Pipeline: {pipeline_steps}\n"
            f"Workflows: {workflows}"
        )

    def _resolve_use_mock(self, request: GenerationRequest) -> bool:
        if request.use_mock is not None:
            return request.use_mock
        return self._config_manager.features.agents.use_mock

    def _select_steps(self, use_mock: bool) -> Sequence[tuple[str, str]]:
        return MOCK_STEP_DEFINITIONS if use_mock else WORKFLOW_STEP_DEFINITIONS

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_text(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _notify(self, job_id: str, callback: Callable[[GenerationJob], None] | None) -> None:
        if not callback:
            return
        snapshot = self._jobs.get(job_id)
        if snapshot:
            callback(snapshot)


pipeline = GenerationPipeline()