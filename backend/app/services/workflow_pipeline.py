"""Pipeline for generating workflow.yaml declaratively using LLM agents."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from fastapi import BackgroundTasks

from ..models.generation import GenerationJob, GenerationRequest, JobStatus, StepStatus
from ..services.jobs import JobRegistry, job_registry
from ..services.workflow_generation import WorkflowGenerationResult, WorkflowGenerator
from ..services.workflow_packaging import WorkflowPackagingService

logger = logging.getLogger(__name__)


class WorkflowGenerationPipeline:
    """Pipeline for generating workflow.yaml using multi-agent LLM workflow."""

    def __init__(
        self,
        jobs: JobRegistry = job_registry,
        working_root: Path = Path("generated"),
        output_root: Path = Path("output"),
    ) -> None:
        self._jobs = jobs
        self._working_root = working_root
        self._working_root.mkdir(parents=True, exist_ok=True)

        self._generator = WorkflowGenerator()
        self._packaging = WorkflowPackagingService(output_root)

    def enqueue(
        self,
        request: GenerationRequest,
        background_tasks: BackgroundTasks,
    ) -> GenerationJob:
        """Enqueue a workflow generation job."""
        job_id = str(uuid4())
        step_definitions = [
            ("analysis", "要件分析"),
            ("architecture", "アーキテクチャ設計"),
            ("yaml_generation", "workflow.yaml生成"),
            ("validation", "検証"),
            ("packaging", "パッケージング"),
        ]
        job = self._jobs.create_job(job_id, request, step_definitions)
        background_tasks.add_task(self._run_job, job.job_id, request)
        logger.info("Enqueued workflow generation job %s", job_id)
        return job

    def _run_job(
        self,
        job_id: str,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> None:
        """Execute workflow generation job."""
        workspace = self._working_root / job_id

        if workspace.exists():
            import shutil

            shutil.rmtree(workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        prompt = (request.requirements_prompt or request.description or "").strip()
        if not prompt:
            raise ValueError("requirements_prompt または description が必要です")

        try:
            self._jobs.update_status(
                job_id,
                step_id="analysis",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="要件を分析しています",
            )
            self._notify(job_id, progress_callback)

            def handle_analysis(_: Any) -> None:
                self._jobs.update_status(
                    job_id,
                    step_id="analysis",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.COMPLETED,
                    message="要件分析が完了しました",
                )
                self._jobs.update_status(
                    job_id,
                    step_id="architecture",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.RUNNING,
                    message="アーキテクチャを設計しています",
                )
                self._notify(job_id, progress_callback)

            def handle_architecture(_: Any) -> None:
                self._jobs.update_status(
                    job_id,
                    step_id="architecture",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.COMPLETED,
                    message="アーキテクチャ設計が完了しました",
                )
                self._jobs.update_status(
                    job_id,
                    step_id="yaml_generation",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.RUNNING,
                    message="workflow.yamlを生成しています",
                )
                self._notify(job_id, progress_callback)

            def handle_yaml(_: str) -> None:
                self._jobs.update_status(
                    job_id,
                    step_id="yaml_generation",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.COMPLETED,
                    message="workflow.yamlの生成が完了しました",
                )
                self._jobs.update_status(
                    job_id,
                    step_id="validation",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.RUNNING,
                    message="検証を実行しています",
                )
                self._notify(job_id, progress_callback)

            def handle_validation(_: Dict[str, Any]) -> None:
                self._jobs.update_status(
                    job_id,
                    step_id="validation",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.COMPLETED,
                    message="検証が完了しました",
                )
                self._notify(job_id, progress_callback)

            result = self._generator.generate(
                prompt,
                on_analysis=handle_analysis,
                on_architecture=handle_architecture,
                on_yaml=handle_yaml,
                on_validation=handle_validation,
            )

            self._jobs.update_status(
                job_id,
                step_id="packaging",
                job_status=JobStatus.PACKAGING,
                step_status=StepStatus.RUNNING,
                message="成果物をパッケージングしています",
            )
            self._notify(job_id, progress_callback)

            job_snapshot = self._jobs.get(job_id)
            if job_snapshot is None:
                raise RuntimeError("Job snapshot missing during packaging")

            if result is None:
                raise RuntimeError("Workflow generation result is missing")

            metadata = self._build_metadata(result)

            zip_path = self._packaging.package_workflow_app(
                job_snapshot,
                result.yaml_content,
                metadata,
            )

            download_url = f"/api/generate/{job_id}/download"
            self._jobs.complete(job_id, download_url, metadata, str(zip_path))
            self._notify(job_id, progress_callback)

            logger.info("Workflow generation job %s completed", job_id)

        except Exception as exc:  # noqa: PERF203
            logger.exception("Workflow generation job %s failed", job_id)
            self._jobs.fail(job_id, str(exc))
            self._notify(job_id, progress_callback)
        finally:
            import shutil

            shutil.rmtree(workspace, ignore_errors=True)

    def _build_metadata(self, result: WorkflowGenerationResult) -> Dict[str, Any]:
        metadata = {
            "workflow_yaml": result.yaml_content,
            "analysis": result.analysis.model_dump() if hasattr(result.analysis, "model_dump") else result.analysis,
            "architecture": result.architecture.model_dump() if hasattr(result.architecture, "model_dump") else result.architecture,
            "validation": dict(result.validation),
        }
        validation_model = metadata["validation"].get("model")
        if validation_model is not None and hasattr(validation_model, "model_dump"):
            metadata["validation"]["model"] = validation_model.model_dump()
        return metadata

    def _notify(
        self,
        job_id: str,
        callback: Callable[[GenerationJob], None] | None,
    ) -> None:
        if not callback:
            return
        snapshot = self._jobs.get(job_id)
        if snapshot:
            callback(snapshot)


# Create singleton instance
workflow_pipeline = WorkflowGenerationPipeline()
