"""LLMベースでworkflow.yamlを生成するパイプライン。"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Callable, Dict
from uuid import uuid4

from fastapi import BackgroundTasks

from ..agents.workflow_agents import AnalystAgent, ArchitectAgent, YAMLSpecialistAgent
from ..models.generation import GenerationJob, GenerationRequest, JobStatus, StepStatus
from .jobs import JobRegistry, job_registry
from .llm_factory import RetryPolicy, llm_factory
from .workflow_packaging import WorkflowPackagingService
from .workflow_validator import SelfCorrectionLoop, WorkflowValidator

logger = logging.getLogger(__name__)


WORKFLOW_STEP_DEFINITIONS = [
    ("analysis", "要件分析"),
    ("architecture", "アーキテクチャ設計"),
    ("yaml_generation", "workflow.yaml生成"),
    ("validation", "バリデーション"),
    ("packaging", "パッケージング"),
]


class GenerationPipeline:
    """workflow.yaml生成に特化したLLMパイプライン。"""

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

    # ------------------------------------------------------------------
    def enqueue(
        self,
        request: GenerationRequest,
        background_tasks: BackgroundTasks,
        *,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> GenerationJob:
        job_id = str(uuid4())
        job = self._jobs.create_job(job_id, request, WORKFLOW_STEP_DEFINITIONS)
        background_tasks.add_task(self._run_job, job.job_id, request, progress_callback)
        logger.info("workflow.yaml生成ジョブ %s をキューに登録しました", job_id)
        return job

    # ------------------------------------------------------------------
    def run_sync(
        self,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> GenerationJob:
        job_id = str(uuid4())
        job = self._jobs.create_job(job_id, request, WORKFLOW_STEP_DEFINITIONS)
        logger.info("workflow.yaml生成ジョブ %s を同期実行します", job_id)
        if progress_callback:
            self._notify(job_id, progress_callback)
        self._run_job(job.job_id, request, progress_callback)
        final_job = self._jobs.get(job_id)
        if final_job is None:
            raise RuntimeError("ジョブの最終状態が保持されていません")
        return final_job

    # ------------------------------------------------------------------
    def _run_job(
        self,
        job_id: str,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> None:
        workspace = self._working_root / job_id

        if workspace.exists():
            shutil.rmtree(workspace)
        workspace.mkdir(parents=True, exist_ok=True)

        try:
            prompt = (request.requirements_prompt or request.description or "").strip()
            if not prompt:
                raise ValueError("requirements_prompt または description を指定してください")

            llm = self._llm_factory.create_chat_model()
            retry_policy: RetryPolicy = self._llm_factory.get_retry_policy()

            # Step 1: 要件分析
            analyst = AnalystAgent(llm, retry_policy)
            self._jobs.update_status(
                job_id,
                step_id="analysis",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="要件を分析しています",
            )
            self._notify(job_id, progress_callback)
            analysis_result = analyst.run(prompt)
            self._jobs.update_status(
                job_id,
                step_id="analysis",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="要件分析が完了しました",
            )
            self._notify(job_id, progress_callback)

            # Step 2: アーキテクチャ設計
            architect = ArchitectAgent(llm, retry_policy)
            self._jobs.update_status(
                job_id,
                step_id="architecture",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="workflow.yamlの骨子を設計しています",
            )
            self._notify(job_id, progress_callback)
            architecture_result = architect.run(analysis_result)
            self._jobs.update_status(
                job_id,
                step_id="architecture",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="アーキテクチャ設計が完了しました",
            )
            self._notify(job_id, progress_callback)

            # Step 3: YAML生成（自己修正ループ）
            self._jobs.update_status(
                job_id,
                step_id="yaml_generation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="workflow.yamlを生成しています",
            )
            self._notify(job_id, progress_callback)

            correction_loop = SelfCorrectionLoop(self._llm_factory, self._validator, max_iterations=3)
            yaml_content, success, errors = correction_loop.generate_with_correction(
                analysis_result,
                architecture_result,
            )

            if not success:
                error_text = "\n".join(errors) or "workflow.yamlの生成に失敗しました"
                raise RuntimeError(error_text)

            self._jobs.update_status(
                job_id,
                step_id="yaml_generation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="workflow.yamlの生成が完了しました",
            )
            self._notify(job_id, progress_callback)

            # Step 4: バリデーション
            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="生成物を検証しています",
            )
            self._notify(job_id, progress_callback)

            validation_result = self._validator.validate_complete(yaml_content)
            if not validation_result["valid"]:
                errors_text = "\n".join(validation_result["all_errors"]) or "バリデーションエラーが発生しました"
                raise RuntimeError(errors_text)

            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="バリデーションが完了しました",
            )
            self._notify(job_id, progress_callback)

            # Step 5: パッケージング
            self._jobs.update_status(
                job_id,
                step_id="packaging",
                job_status=JobStatus.PACKAGING,
                step_status=StepStatus.RUNNING,
                message="配布パッケージを作成しています",
            )
            self._notify(job_id, progress_callback)

            job_snapshot = self._jobs.get(job_id)
            if job_snapshot is None:
                raise RuntimeError("ジョブ情報が失われました")

            validation_metadata: Dict[str, Any] = dict(validation_result)
            validation_model = validation_metadata.get("model")
            if validation_model is not None and hasattr(validation_model, "model_dump"):
                validation_metadata["model"] = validation_model.model_dump()

            metadata = {
                "workflow_yaml": yaml_content,
                "analysis": analysis_result.model_dump(),
                "architecture": architecture_result.model_dump(),
                "validation": validation_metadata,
                "request": request.model_dump(),
            }

            zip_path = self._packaging.package_workflow_app(
                job_snapshot,
                workflow_yaml=yaml_content,
                metadata=metadata,
            )

            download_url = f"/api/generate/{job_id}/download"
            self._jobs.complete(job_id, download_url, metadata, str(zip_path))
            self._notify(job_id, progress_callback)

            logger.info("workflow.yaml生成ジョブ %s が完了しました", job_id)

        except Exception as exc:  # noqa: PERF203 - 失敗時に必ず記録
            logger.exception("workflow.yaml生成ジョブ %s が失敗しました", job_id)
            self._jobs.fail(job_id, str(exc))
            self._notify(job_id, progress_callback)
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    # ------------------------------------------------------------------
    def _notify(
        self,
        job_id: str,
        callback: Callable[[GenerationJob], None] | None,
    ) -> None:
        if not callback:
            return
        snapshot = self._jobs.get(job_id)
        if snapshot is not None:
            callback(snapshot)


pipeline = GenerationPipeline()
