"""Generation pipeline orchestrating mock agent, templates, and packaging."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Callable
from uuid import uuid4

from fastapi import BackgroundTasks

from ..config import ConfigManager, config_manager
from ..models.generation import GenerationJob, GenerationRequest, JobStatus, StepStatus
from .jobs import JobRegistry, job_registry
from .llm_factory import llm_factory
from .packaging import PackagingService
from .templates import TemplateRenderer

logger = logging.getLogger(__name__)


class GenerationPipeline:
    def __init__(
        self,
        config_manager: ConfigManager = config_manager,
        jobs: JobRegistry = job_registry,
        working_root: Path = Path("generated"),
    ) -> None:
        self._config_manager = config_manager
        self._jobs = jobs

        features = self._config_manager.features
        template_root = Path(features.generation.template_root)
        self._llm_factory = llm_factory
        self._template_renderer = TemplateRenderer(template_root)
        self._packaging = PackagingService(Path(features.generation.output_root))
        self._working_root = working_root
        self._working_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def enqueue(self, request: GenerationRequest, background_tasks: BackgroundTasks) -> GenerationJob:
        job_id = str(uuid4())
        job = self._jobs.create_job(job_id, request)
        background_tasks.add_task(self._run_job, job.job_id, request)
        logger.info("Enqueued generation job %s", job_id)
        return job

    # ------------------------------------------------------------------
    def run_sync(
        self,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> GenerationJob:
        job_id = str(uuid4())
        job = self._jobs.create_job(job_id, request)
        logger.info("Running generation job %s synchronously", job_id)
        if progress_callback:
            self._notify(job_id, progress_callback)
        self._run_job(job_id, request, progress_callback=progress_callback)
        final_job = self._jobs.get(job_id)
        if final_job is None:
            raise RuntimeError("Job finished without persisted state")
        return final_job

    # ------------------------------------------------------------------
    def _run_job(
        self,
        job_id: str,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None = None,
    ) -> None:
        workspace = self._working_root / job_id
        artifacts_dir = workspace / "artifacts"

        if workspace.exists():
            shutil.rmtree(workspace)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._jobs.update_status(
                job_id,
                step_id="requirements",
                job_status=JobStatus.RECEIVED,
                step_status=StepStatus.COMPLETED,
                message="要件を受理しました",
            )
            self._notify(job_id, progress_callback)
            self._jobs.update_status(
                job_id,
                step_id="mock_agent",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="モック仕様を生成しています",
            )
            self._notify(job_id, progress_callback)
            agent = self._llm_factory.create_mock_agent(request.mock_spec_id)
            spec = agent.generate_spec(request.mock_spec_id)
            (workspace / "spec.json").write_text(
                json.dumps(spec, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._jobs.update_status(
                job_id,
                step_id="mock_agent",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="モック仕様の生成が完了しました",
            )
            self._notify(job_id, progress_callback)

            self._jobs.update_status(
                job_id,
                step_id="preview",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="モックプレビューを準備しています",
            )
            self._notify(job_id, progress_callback)
            self._jobs.update_status(
                job_id,
                step_id="preview",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="モックプレビューを配信しました",
            )
            self._notify(job_id, progress_callback)

            context = self._build_template_context(request, spec)
            self._jobs.update_status(
                job_id,
                step_id="template_generation",
                job_status=JobStatus.TEMPLATES_RENDERING,
                step_status=StepStatus.RUNNING,
                message="テンプレートをレンダリングしています",
            )
            self._notify(job_id, progress_callback)
            self._template_renderer.render_to_directory(artifacts_dir, context)
            self._jobs.update_status(
                job_id,
                step_id="template_generation",
                job_status=JobStatus.TEMPLATES_RENDERING,
                step_status=StepStatus.COMPLETED,
                message="テンプレートのレンダリングが完了しました",
            )
            self._notify(job_id, progress_callback)

            self._jobs.update_status(
                job_id,
                step_id="backend_setup",
                job_status=JobStatus.TEMPLATES_RENDERING,
                step_status=StepStatus.RUNNING,
                message="バックエンド設定を適用しています",
            )
            self._notify(job_id, progress_callback)
            self._jobs.update_status(
                job_id,
                step_id="backend_setup",
                job_status=JobStatus.TEMPLATES_RENDERING,
                step_status=StepStatus.COMPLETED,
                message="バックエンド設定が完了しました",
            )
            self._notify(job_id, progress_callback)

            self._jobs.update_status(
                job_id,
                step_id="testing",
                job_status=JobStatus.TEMPLATES_RENDERING,
                step_status=StepStatus.RUNNING,
                message="テストリソースを準備しています",
            )
            self._notify(job_id, progress_callback)
            self._jobs.update_status(
                job_id,
                step_id="testing",
                job_status=JobStatus.TEMPLATES_RENDERING,
                step_status=StepStatus.COMPLETED,
                message="テストテンプレートが準備できました",
            )
            self._notify(job_id, progress_callback)

            job_snapshot = self._jobs.get(job_id)
            if job_snapshot is None:
                raise RuntimeError("Job snapshot missing during packaging")

            metadata = self._build_metadata(request, spec)

            self._jobs.update_status(
                job_id,
                step_id="packaging",
                job_status=JobStatus.PACKAGING,
                step_status=StepStatus.RUNNING,
                message="成果物をパッケージングしています",
            )
            self._notify(job_id, progress_callback)
            zip_path = self._packaging.package(job_snapshot, artifacts_dir, metadata)

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
    def _build_template_context(self, request: GenerationRequest, spec: Dict[str, Any]) -> Dict[str, Any]:
        bundle = self._config_manager.load()
        return {
            "request": request.model_dump(),
            "spec": spec,
            "config": bundle.model_dump(),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }

    def _build_metadata(self, request: GenerationRequest, spec: Dict[str, Any]) -> Dict[str, Any]:
        metadata = {
            "request": request.model_dump(),
            "spec": spec,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "config": self._config_manager.export_metadata(),
        }
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


pipeline = GenerationPipeline()


