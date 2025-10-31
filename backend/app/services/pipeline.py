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
from .agents import (
    Agent1Output,
    Agent2Output,
    Agent3Output,
    Agent4Output,
    AppTypeClassificationAgent,
    ComponentSelectionAgent,
    DataFlowDesignAgent,
    RequirementsDecompositionAgent,
    ValidatorAgent,
)
from .agents.catalog import get_ui_parts_catalog
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

            # Check if we should use mock or LLM mode
            use_mock = self._config_manager.features.agents.use_mock

            if use_mock:
                spec = self._run_mock_pipeline(job_id, request, progress_callback, workspace)
            else:
                spec = self._run_llm_pipeline(job_id, request, progress_callback, workspace)

            (workspace / "spec.json").write_text(
                json.dumps(spec, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

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

    def _run_mock_pipeline(
        self,
        job_id: str,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None,
        workspace: Path,
    ) -> Dict[str, Any]:
        """Run the mock agent pipeline (Phase 1 mode)."""
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
        return spec

    def _run_llm_pipeline(
        self,
        job_id: str,
        request: GenerationRequest,
        progress_callback: Callable[[GenerationJob], None] | None,
        workspace: Path,
    ) -> Dict[str, Any]:
        """Run the LLM agent pipeline (Phase 2 mode)."""
        ui_catalog = get_ui_parts_catalog()

        # Agent 1: Requirements Decomposition
        self._jobs.update_status(
            job_id,
            step_id="agent1_requirements",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.RUNNING,
            message="要件を分解しています",
        )
        self._notify(job_id, progress_callback)
        agent1 = RequirementsDecompositionAgent()
        agent1_output = agent1.run({"description": request.description})
        self._jobs.update_status(
            job_id,
            step_id="agent1_requirements",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.COMPLETED,
            message="要件分解が完了しました",
        )
        self._notify(job_id, progress_callback)

        # Agent 2: App Type Classification
        self._jobs.update_status(
            job_id,
            step_id="agent2_classification",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.RUNNING,
            message="アプリタイプを分類しています",
        )
        self._notify(job_id, progress_callback)
        agent2 = AppTypeClassificationAgent()
        agent2_output = agent2.run(
            {
                "requirements": [req.model_dump() for req in agent1_output.requirements],
                "summary": agent1_output.summary,
            }
        )
        self._jobs.update_status(
            job_id,
            step_id="agent2_classification",
            job_status=JobStatus.SPEC_GENERATING,
            step_status=StepStatus.COMPLETED,
            message=f"アプリタイプを分類しました: {agent2_output.app_type.value}",
        )
        self._notify(job_id, progress_callback)

        # Agent 3: Component Selection (with retry logic)
        max_retries = 3
        agent3_output = None
        validator_output = None

        for retry_count in range(max_retries):
            step_id = f"agent3_selection" if retry_count == 0 else f"agent3_selection_retry_{retry_count}"
            self._jobs.update_status(
                job_id,
                step_id=step_id,
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message=f"コンポーネントを選択しています{' (再試行 ' + str(retry_count) + ')' if retry_count > 0 else ''}",
            )
            self._notify(job_id, progress_callback)

            agent3 = ComponentSelectionAgent(ui_parts_catalog=ui_catalog)
            agent3_output = agent3.run(
                {
                    "requirements": [req.model_dump() for req in agent1_output.requirements],
                    "app_type": agent2_output.app_type.value,
                }
            )
            self._jobs.update_status(
                job_id,
                step_id=step_id,
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="コンポーネント選択が完了しました",
            )
            self._notify(job_id, progress_callback)

            # Agent 4: Data Flow Design
            self._jobs.update_status(
                job_id,
                step_id="agent4_dataflow",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="データフローを設計しています",
            )
            self._notify(job_id, progress_callback)
            agent4 = DataFlowDesignAgent()
            agent4_output = agent4.run(
                {
                    "requirements": [req.model_dump() for req in agent1_output.requirements],
                    "app_type": agent2_output.app_type.value,
                    "components": [comp.model_dump() for comp in agent3_output.components],
                }
            )
            self._jobs.update_status(
                job_id,
                step_id="agent4_dataflow",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.COMPLETED,
                message="データフロー設計が完了しました",
            )
            self._notify(job_id, progress_callback)

            # Validator
            self._jobs.update_status(
                job_id,
                step_id="validator",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=StepStatus.RUNNING,
                message="仕様を検証しています",
            )
            self._notify(job_id, progress_callback)
            validator = ValidatorAgent(ui_parts_catalog=ui_catalog)
            validator_output = validator.run(
                {
                    "requirements": [req.model_dump() for req in agent1_output.requirements],
                    "app_type": agent2_output.app_type.value,
                    "components": [comp.model_dump() for comp in agent3_output.components],
                    "data_flow": [step.model_dump() for step in agent4_output.data_flow],
                }
            )
            self._jobs.update_status(
                job_id,
                step_id="validator",
                job_status=JobStatus.SPEC_GENERATING,
                step_status=validator_output.is_valid and StepStatus.COMPLETED or StepStatus.RUNNING,
                message="検証が完了しました" if validator_output.is_valid else f"検証エラー: {len(validator_output.errors)}件",
            )
            self._notify(job_id, progress_callback)

            if validator_output.is_valid:
                break

            # If validation failed and we have retries left, prepare feedback for Agent 3
            if retry_count < max_retries - 1:
                logger.warning(
                    "Validation failed (attempt %d/%d). Retrying Agent 3 with error feedback.",
                    retry_count + 1,
                    max_retries,
                )
                # In a more sophisticated implementation, we could pass validation errors to Agent 3
                # For now, we just retry
            else:
                # All retries exhausted
                error_messages = [f"{err.rule}: {err.message}" for err in validator_output.errors]
                raise ValueError(f"Validation failed after {max_retries} attempts. Errors: {', '.join(error_messages)}")

        if not validator_output or not validator_output.is_valid:
            raise ValueError("Specification validation failed")

        # Convert agent outputs to specification format
        spec = self._convert_to_spec_format(
            agent1_output, agent2_output, agent3_output, agent4_output, request
        )
        return spec

    def _convert_to_spec_format(
        self,
        agent1: Agent1Output,
        agent2: Agent2Output,
        agent3: Agent3Output,
        agent4: Agent4Output,
        request: GenerationRequest,
    ) -> Dict[str, Any]:
        """Convert agent outputs to the specification format expected by templates."""
        # Build forms from components
        forms = []
        components_by_step: Dict[int, list] = {}
        for comp in agent3.components:
            step = comp.position.step
            if step not in components_by_step:
                components_by_step[step] = []
            components_by_step[step].append(comp)

        for step_num, components in sorted(components_by_step.items()):
            fields = []
            for comp in components:
                field: Dict[str, Any] = {
                    "name": comp.component_id,
                    "label": comp.props.label or comp.component_id,
                    "type": comp.props.type or comp.component_id.split("_")[0],
                }
                if comp.props.placeholder:
                    field["placeholder"] = comp.props.placeholder
                if comp.props.required is not None:
                    field["required"] = comp.props.required
                if comp.props.options:
                    field["options"] = comp.props.options
                fields.append(field)

            if fields:
                forms.append({"step": step_num, "title": f"Step {step_num}", "fields": fields})

        # Build backend routes from data flow
        routes = []
        for flow_step in agent4.data_flow:
            if flow_step.api_call:
                route: Dict[str, Any] = {
                    "path": flow_step.api_call.get("path", "/api/endpoint"),
                    "method": flow_step.api_call.get("method", "POST"),
                    "summary": flow_step.api_call.get("summary", ""),
                }
                routes.append(route)

        spec: Dict[str, Any] = {
            "app": {
                "name": request.project_name,
                "slug": request.project_id,
                "summary": request.description,
                "version": "0.1.0",
                "owner": {
                    "team": "Generated",
                    "contact": request.user_id,
                },
            },
            "frontend": {
                "wizard": {
                    "steps": ["要件入力", "設計プレビュー", "UI モック承認", "テンプレート生成", "バックエンド設定", "テスト準備", "成果物ダウンロード"],
                    "primary_color": "#1976d2",
                    "accent_color": "#009688",
                },
                "forms": forms,
            },
            "backend": {
                "routes": routes,
                "models": [],
                "validation_rules": [],
            },
            "tests": {
                "playwright": {
                    "scenarios": [
                        {
                            "name": "wizard-happy-path",
                            "description": "Completes the wizard and downloads the generated zip",
                        }
                    ],
                },
            },
            "docker": {
                "services": [
                    {"name": "web", "description": "React frontend"},
                    {"name": "api", "description": "FastAPI backend"},
                ],
            },
        }
        return spec

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


