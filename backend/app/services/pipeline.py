"""Generation pipeline orchestrating mock agent, templates, and packaging."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence
from uuid import uuid4

from fastapi import BackgroundTasks

from ..agents import (
    AppTypeClassificationAgent,
    ComponentSelectionAgent,
    DataFlowDesignAgent,
    RequirementsDecompositionAgent,
    SpecificationValidatorAgent,
)
from ..agents.models import (
    AppTypeClassificationResult,
    ComponentSelectionResult,
    DataFlowDesignResult,
    RequirementsDecompositionResult,
    ValidationResult,
)
from ..config import ConfigManager, config_manager
from ..models.generation import GenerationJob, GenerationRequest, JobStatus, StepStatus
from ..services.ui_catalog import load_ui_catalog
from .jobs import JobRegistry, job_registry
from .llm_factory import RetryPolicy, llm_factory
from .packaging import PackagingService
from .templates import TemplateRenderer

logger = logging.getLogger(__name__)


MOCK_STEP_DEFINITIONS: Sequence[tuple[str, str]] = (
    ("requirements", "要件受付"),
    ("mock_agent", "モック仕様生成"),
    ("preview", "モックプレビュー"),
    ("template_generation", "テンプレート生成"),
    ("backend_setup", "バックエンド構築"),
    ("testing", "テスト準備"),
    ("packaging", "成果物パッケージ"),
)

LLM_STEP_DEFINITIONS: Sequence[tuple[str, str]] = (
    ("requirements", "要件受付"),
    ("requirements_decomposition", "要件分解"),
    ("app_type_classification", "アプリタイプ分類"),
    ("component_selection", "コンポーネント選定"),
    ("data_flow_design", "データフロー設計"),
    ("validation", "仕様バリデーション"),
    ("template_generation", "テンプレート生成"),
    ("backend_setup", "バックエンド構築"),
    ("testing", "テスト準備"),
    ("packaging", "成果物パッケージ"),
)

LLM_VALIDATION_MAX_ATTEMPTS = 3


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
        self._catalog = load_ui_catalog()

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
        self._run_job(
            job_id,
            request,
            use_mock,
            progress_callback=progress_callback,
        )
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
        artifacts_dir = workspace / "artifacts"

        if workspace.exists():
            shutil.rmtree(workspace)
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        spec: Dict[str, Any] | None = None

        try:
            self._jobs.update_status(
                job_id,
                step_id="requirements",
                job_status=JobStatus.RECEIVED,
                step_status=StepStatus.COMPLETED,
                message="要件を受理しました",
            )
            self._notify(job_id, progress_callback)

            if use_mock:
                spec = self._run_mock_pipeline(job_id, request, workspace, progress_callback)
            else:
                spec = self._run_llm_pipeline(job_id, request, workspace, progress_callback)

            self._write_json(workspace / "spec.json", spec)

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

    def _run_mock_pipeline(
        self,
        job_id: str,
        request: GenerationRequest,
        workspace: Path,
        progress_callback: Callable[[GenerationJob], None] | None,
    ) -> Dict[str, Any]:
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

        return spec

    def _run_llm_pipeline(
        self,
        job_id: str,
        request: GenerationRequest,
        workspace: Path,
        progress_callback: Callable[[GenerationJob], None] | None,
    ) -> Dict[str, Any]:
        prompt = (request.requirements_prompt or request.description or "").strip()
        if not prompt:
            raise ValueError("LLMモードでは requirements_prompt または description が必要です")

        llm = self._llm_factory.create_chat_model()
        retry_policy: RetryPolicy = self._llm_factory.get_retry_policy()

        requirements_agent = RequirementsDecompositionAgent(llm, retry_policy)
        classification_agent = AppTypeClassificationAgent(llm, retry_policy)
        component_agent = ComponentSelectionAgent(llm, retry_policy)
        data_flow_agent = DataFlowDesignAgent(llm, retry_policy)
        validator_agent = SpecificationValidatorAgent(llm, retry_policy)

        self._jobs.update_status(
            job_id,
            step_id="requirements_decomposition",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.RUNNING,
            message="要件を分解しています",
        )
        self._notify(job_id, progress_callback)
        requirements_result = requirements_agent.run(prompt)
        self._write_json(workspace / "requirements_decomposition.json", requirements_result.model_dump())
        self._jobs.update_status(
            job_id,
            step_id="requirements_decomposition",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.COMPLETED,
            message="要件分解が完了しました",
        )
        self._notify(job_id, progress_callback)

        self._jobs.update_status(
            job_id,
            step_id="app_type_classification",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.RUNNING,
            message="アプリタイプを分類しています",
        )
        self._notify(job_id, progress_callback)
        classification_result = classification_agent.run(requirements_result)
        self._write_json(workspace / "app_type_classification.json", classification_result.model_dump())
        self._jobs.update_status(
            job_id,
            step_id="app_type_classification",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.COMPLETED,
            message="アプリタイプ分類が完了しました",
        )
        self._notify(job_id, progress_callback)

        # Prepare steps for iterative selection/validation
        self._jobs.update_status(
            job_id,
            step_id="component_selection",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.RUNNING,
            message="コンポーネントを選定しています",
        )
        self._notify(job_id, progress_callback)

        feedback: str | None = None
        component_result: ComponentSelectionResult | None = None
        data_flow_result: DataFlowDesignResult | None = None
        validation_result: ValidationResult | None = None

        for attempt in range(1, LLM_VALIDATION_MAX_ATTEMPTS + 1):
            attempt_message = f"コンポーネント選定を実行中 (試行 {attempt}/{LLM_VALIDATION_MAX_ATTEMPTS})"
            self._jobs.update_status(
                job_id,
                step_id="component_selection",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message=attempt_message,
                log_entry=feedback,
            )
            self._notify(job_id, progress_callback)

            component_result = component_agent.run(requirements_result, classification_result, self._catalog, feedback=feedback)
            self._write_json(
                workspace / f"component_selection_attempt_{attempt}.json",
                component_result.model_dump(),
            )

            self._jobs.update_status(
                job_id,
                step_id="data_flow_design",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message=f"データフローを設計しています (試行 {attempt})",
            )
            self._notify(job_id, progress_callback)

            data_flow_result = data_flow_agent.run(requirements_result, classification_result, component_result)
            self._write_json(
                workspace / f"data_flow_design_attempt_{attempt}.json",
                data_flow_result.model_dump(),
            )
            self._jobs.update_status(
                job_id,
                step_id="data_flow_design",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="データフロー設計が完了しました",
            )
            self._notify(job_id, progress_callback)

            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message=f"仕様を検証しています (試行 {attempt})",
            )
            self._notify(job_id, progress_callback)

            validation_result = validator_agent.run(requirements_result, component_result, data_flow_result, self._catalog)
            self._write_json(
                workspace / f"validation_attempt_{attempt}.json",
                validation_result.model_dump(),
            )

            if validation_result.success:
                self._jobs.update_status(
                    job_id,
                    step_id="validation",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.COMPLETED,
                    message="仕様バリデーションが完了しました",
                )
                self._jobs.update_status(
                    job_id,
                    step_id="component_selection",
                    job_status=JobStatus.SPEC_GENERATING,
                    step_status=StepStatus.COMPLETED,
                    message="コンポーネント選定が完了しました",
                )
                self._notify(job_id, progress_callback)
                break

            feedback = self._format_validation_feedback(validation_result)
            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="バリデーションで修正が必要です。コンポーネントを再試行します。",
                log_entry=feedback,
            )
            self._notify(job_id, progress_callback)
        else:  # Exhausted retries
            failure_message = feedback or "仕様バリデーションに失敗しました"
            self._jobs.update_status(
                job_id,
                step_id="validation",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.FAILED,
                message=failure_message,
            )
            raise RuntimeError(failure_message)

        assert component_result is not None
        assert data_flow_result is not None
        assert validation_result is not None

        spec = self._build_llm_spec(
            request,
            prompt,
            requirements_result,
            classification_result,
            component_result,
            data_flow_result,
            validation_result,
        )
        return spec

    def _build_llm_spec(
        self,
        request: GenerationRequest,
        prompt: str,
        requirements: RequirementsDecompositionResult,
        classification: AppTypeClassificationResult,
        components: ComponentSelectionResult,
        data_flow: DataFlowDesignResult,
        validation: ValidationResult,
    ) -> Dict[str, Any]:
        return {
            "app": {
                "name": request.project_name,
                "slug": request.project_id,
                "summary": requirements.summary,
                "version": "0.2.0",
                "type": classification.app_type,
                "template": classification.recommended_template,
            },
            "source": {
                "requirements_prompt": prompt,
                "description": request.description,
            },
            "requirements": requirements.model_dump(),
            "classification": classification.model_dump(),
            "components": components.model_dump(),
            "data_flow": data_flow.model_dump(),
            "validation": validation.model_dump(),
        }

    def _format_validation_feedback(self, validation: ValidationResult) -> str:
        if not validation.errors:
            return "Validator returned no issues but success=false"
        lines: List[str] = []
        for issue in validation.errors:
            level = issue.level.upper()
            line = f"[{level}] {issue.code}: {issue.message}"
            if issue.hint:
                line += f" (hint: {issue.hint})"
            lines.append(line)
        return "\n".join(lines)

    def _resolve_use_mock(self, request: GenerationRequest) -> bool:
        if request.use_mock is not None:
            return request.use_mock
        return self._config_manager.features.agents.use_mock

    def _select_steps(self, use_mock: bool) -> Sequence[tuple[str, str]]:
        return MOCK_STEP_DEFINITIONS if use_mock else LLM_STEP_DEFINITIONS

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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


