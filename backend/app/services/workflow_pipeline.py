"""Pipeline for generating workflow.yaml declaratively using LLM agents."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from fastapi import BackgroundTasks

from ..agents.workflow_agents import (
    AnalystAgent,
    ArchitectAgent,
    YAMLSpecialistAgent,
)
from ..services.workflow_validator import SelfCorrectionLoop, WorkflowValidator
from ..services.workflow_packaging import WorkflowPackagingService
from ..models.generation import GenerationJob, GenerationRequest, JobStatus, StepStatus
from ..services.jobs import JobRegistry, job_registry
from ..services.llm_factory import llm_factory

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
        
        self._llm_factory = llm_factory
        self._validator = WorkflowValidator(llm_factory)
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
            ("yaml_generation", "workflow.yaml 生成"),
            ("validation", "仕様バリデーション"),
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
        
        try:
            # Step 1: Analysis
            self._jobs.update_status(
                job_id,
                step_id="analysis",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="要件を解析しています",
            )
            self._notify(job_id, progress_callback)

            prompt = (request.requirements_prompt or request.description or "").strip()
            if not prompt:
                raise ValueError("requirements_prompt または description のいずれかは必須です")
            
            llm = self._llm_factory.create_chat_model()
            retry_policy = self._llm_factory.get_retry_policy()
            
            analyst = AnalystAgent(llm, retry_policy)
            analysis_result = analyst.run(prompt)
            
            self._jobs.update_status(
                job_id,
                step_id="analysis",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="要件分析が完了しました",
            )
            self._notify(job_id, progress_callback)
            
            # Step 2: Architecture
            self._jobs.update_status(
                job_id,
                step_id="architecture",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="ワークフロー構造を設計しています",
            )
            self._notify(job_id, progress_callback)
            
            architect = ArchitectAgent(llm, retry_policy)
            architecture_result = architect.run(analysis_result)
            
            self._jobs.update_status(
                job_id,
                step_id="architecture",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="アーキテクチャ設計が完了しました",
            )
            self._notify(job_id, progress_callback)
            
            # Step 3: YAML Generation with Self-Correction
            self._jobs.update_status(
                job_id,
                step_id="yaml_generation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="workflow.yaml を生成しています",
            )
            self._notify(job_id, progress_callback)
            
            correction_loop = SelfCorrectionLoop(
                self._llm_factory,
                self._validator,
                max_iterations=3,
            )
            
            yaml_content, success, errors = correction_loop.generate_with_correction(
                analysis_result,
                architecture_result,
            )
            
            if not success:
                raise RuntimeError(f"workflow.yaml の生成に失敗しました: {'; '.join(errors)}")
            
            self._jobs.update_status(
                job_id,
                step_id="yaml_generation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="workflow.yaml の生成が完了しました",
            )
            self._notify(job_id, progress_callback)
            
            # Step 4: Validation
            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="生成された workflow.yaml を検証しています",
            )
            self._notify(job_id, progress_callback)
            
            validation_result = self._validator.validate_complete(yaml_content)
            if not validation_result["valid"]:
                raise RuntimeError(
                    f"workflow.yaml の検証に失敗しました: {'; '.join(validation_result['all_errors'])}"
                )
            
            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="workflow.yaml の検証が完了しました",
            )
            self._notify(job_id, progress_callback)
            
            # Step 5: Packaging
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
                raise RuntimeError("パッケージング中にジョブ情報を取得できませんでした")
            
            validation_metadata = dict(validation_result)
            validation_model = validation_metadata.get("model")
            if validation_model is not None and hasattr(validation_model, "model_dump"):
                validation_metadata["model"] = validation_model.model_dump()

            metadata = {
                "workflow_yaml": yaml_content,
                "analysis": analysis_result.model_dump(),
                "architecture": architecture_result.model_dump(),
                "validation": validation_metadata,
            }
            
            zip_path = self._packaging.package_workflow_app(
                job_snapshot,
                yaml_content,
                metadata,
            )
            
            download_url = f"/api/generate/{job_id}/download"
            self._jobs.complete(job_id, download_url, metadata, str(zip_path))
            self._notify(job_id, progress_callback)
            
            logger.info("Workflow generation job %s completed", job_id)
            
        except Exception as exc:
            logger.exception("Workflow generation job %s failed", job_id)
            self._jobs.fail(job_id, str(exc))
            self._notify(job_id, progress_callback)
        finally:
            import shutil
            shutil.rmtree(workspace, ignore_errors=True)
    
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
