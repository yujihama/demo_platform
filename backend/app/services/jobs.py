"""In-memory job registry for Phase 1."""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any, Dict, Iterable, Optional

from ..config import ConfigManager, config_manager
from ..models.generation import (
    GenerationJob,
    GenerationRequest,
    JobStatus,
    JobStep,
    StepStatus,
)

MOCK_STEP_DEFINITIONS = [
    ("requirements", "要件受付"),
    ("mock_agent", "モック仕様生成"),
    ("preview", "モックプレビュー"),
    ("template_generation", "テンプレート生成"),
    ("backend_setup", "バックエンド構築"),
    ("testing", "テスト準備"),
    ("packaging", "成果物パッケージ"),
]

LLM_STEP_DEFINITIONS = [
    ("requirements", "要件受付"),
    ("agent1_requirements", "要件分解"),
    ("agent2_classification", "アプリタイプ分類"),
    ("agent3_selection", "コンポーネント選定"),
    ("agent3_selection_retry_1", "コンポーネント再選定 (1回目)"),
    ("agent3_selection_retry_2", "コンポーネント再選定 (2回目)"),
    ("agent4_dataflow", "データフロー設計"),
    ("validator", "仕様検証"),
    ("preview", "モックプレビュー"),
    ("template_generation", "テンプレート生成"),
    ("backend_setup", "バックエンド構築"),
    ("testing", "テスト準備"),
    ("packaging", "成果物パッケージ"),
]


class JobRegistry:
    """Thread-safe in-memory store that tracks generation jobs."""

    def __init__(self, config_manager: ConfigManager = config_manager) -> None:
        self._jobs: Dict[str, GenerationJob] = {}
        self._lock = Lock()
        self._config_manager = config_manager

    def _resolve_step_definitions(self) -> Iterable[tuple[str, str]]:
        """Return step definitions based on whether the mock pipeline is enabled."""

        try:
            use_mock = self._config_manager.features.agents.use_mock
        except Exception:  # pragma: no cover - defensive fallback
            use_mock = True
        return MOCK_STEP_DEFINITIONS if use_mock else LLM_STEP_DEFINITIONS

    # ------------------------------------------------------------------
    def create_job(self, job_id: str, request: GenerationRequest) -> GenerationJob:
        steps = [
            JobStep(id=step_id, label=label, status=StepStatus.PENDING)
            for step_id, label in self._resolve_step_definitions()
        ]
        if steps:
            steps[0].status = StepStatus.RUNNING

        job = GenerationJob(
            job_id=job_id,
            user_id=request.user_id,
            project_id=request.project_id,
            project_name=request.project_name,
            description=request.description,
            status=JobStatus.RECEIVED,
            steps=steps,
        )

        with self._lock:
            self._jobs[job_id] = job
        return job

    # ------------------------------------------------------------------
    def get(self, job_id: str) -> Optional[GenerationJob]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return job.model_copy(deep=True)

    # ------------------------------------------------------------------
    def list_jobs(self) -> Iterable[GenerationJob]:
        with self._lock:
            for job in self._jobs.values():
                yield job.model_copy(deep=True)

    # ------------------------------------------------------------------
    def update_status(
        self,
        job_id: str,
        step_id: str,
        job_status: Optional[JobStatus] = None,
        step_status: Optional[StepStatus] = None,
        message: Optional[str] = None,
        log_entry: Optional[str] = None,
    ) -> GenerationJob:
        with self._lock:
            job = self._jobs[job_id]
            if job_status is not None:
                job.status = job_status
            job.updated_at = datetime.utcnow()

            target_index: Optional[int] = None
            for idx, step in enumerate(job.steps):
                if step.id == step_id:
                    target_index = idx
                    if step_status is not None:
                        step.status = step_status
                    if message:
                        step.message = message
                    if log_entry:
                        step.logs.append(log_entry)

            if (
                step_status == StepStatus.COMPLETED
                and target_index is not None
                and target_index + 1 < len(job.steps)
            ):
                next_step = job.steps[target_index + 1]
                if next_step.status == StepStatus.PENDING:
                    next_step.status = StepStatus.RUNNING
                    next_step.message = "進行中"

            self._jobs[job_id] = job
            return job.model_copy(deep=True)

    # ------------------------------------------------------------------
    def complete(
        self,
        job_id: str,
        download_url: str,
        metadata: Dict[str, Any],
        output_path: str,
    ) -> GenerationJob:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.COMPLETED
            job.download_url = download_url
            job.metadata = metadata
            job.output_path = output_path
            job.updated_at = datetime.utcnow()
            for step in job.steps:
                if step.status != StepStatus.FAILED:
                    step.status = StepStatus.COMPLETED
            self._jobs[job_id] = job
            return job.model_copy(deep=True)

    # ------------------------------------------------------------------
    def fail(self, job_id: str, message: str) -> GenerationJob:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.FAILED
            job.updated_at = datetime.utcnow()
            for step in job.steps:
                if step.status not in {StepStatus.COMPLETED, StepStatus.FAILED}:
                    step.status = StepStatus.FAILED
                    step.message = message
            self._jobs[job_id] = job
            return job.model_copy(deep=True)


job_registry = JobRegistry()


