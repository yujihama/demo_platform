"""LLM対話セッションを管理するサービス。"""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Dict
from uuid import uuid4

from fastapi import BackgroundTasks

from ..models.conversation import (
    ConversationMessage,
    ConversationSession,
    ConversationStartRequest,
    ConversationStartResponse,
    ConversationStatusResponse,
    WorkflowContentResponse,
)
from ..models.generation import GenerationJob, JobStatus
from .pipeline import GenerationPipeline, pipeline


class ConversationManager:
    """対話セッションを永続化し、パイプラインの進捗と同期する。"""

    def __init__(self, storage_root: Path = Path("generated/conversations")) -> None:
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = Lock()
        self._storage_root = storage_root
        self._storage_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def start_conversation(
        self,
        payload: ConversationStartRequest,
        background_tasks: BackgroundTasks,
        *,
        generation_pipeline: GenerationPipeline = pipeline,
    ) -> ConversationStartResponse:
        session_id = str(uuid4())
        request = payload.to_generation_request()

        def progress(job: GenerationJob) -> None:
            self._handle_job_update(session_id, job)

        job = generation_pipeline.enqueue(request, background_tasks, progress_callback=progress)

        initial_messages = [
            ConversationMessage(role="user", content=payload.prompt),
            ConversationMessage(
                role="assistant",
                content="要件を受け取りました。workflow.yamlの生成を開始します。",
            ),
        ]

        session = ConversationSession(
            session_id=session_id,
            job_id=job.job_id,
            status=job.status,
            messages=initial_messages,
        )

        with self._lock:
            self._sessions[session_id] = session

        return ConversationStartResponse(
            session_id=session_id,
            job_id=job.job_id,
            status=job.status,
            messages=list(initial_messages),
        )

    # ------------------------------------------------------------------
    def get_session(self, session_id: str) -> ConversationStatusResponse:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            snapshot = session.model_copy(deep=True)
        return ConversationStatusResponse(
            session_id=snapshot.session_id,
            job_id=snapshot.job_id,
            status=snapshot.status,
            messages=snapshot.messages,
            workflow_ready=snapshot.workflow_ready,
            download_url=snapshot.download_url,
        )

    # ------------------------------------------------------------------
    def get_workflow(self, session_id: str) -> WorkflowContentResponse:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            if not session.workflow_path:
                raise FileNotFoundError("workflow.yaml はまだ生成されていません")
            workflow_path = Path(session.workflow_path)
        if not workflow_path.exists():
            raise FileNotFoundError("workflow.yaml が保存されていません")
        content = workflow_path.read_text(encoding="utf-8")
        return WorkflowContentResponse(workflow=content)

    # ------------------------------------------------------------------
    def get_package_url(self, session_id: str) -> str | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(session_id)
            return session.download_url

    # ------------------------------------------------------------------
    def _handle_job_update(self, session_id: str, job: GenerationJob) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return

            session.status = job.status
            session.download_url = job.download_url

            if job.status == JobStatus.COMPLETED:
                if not session.workflow_ready:
                    workflow_yaml = (job.metadata or {}).get("workflow_yaml")
                    if workflow_yaml:
                        path = self._write_workflow_file(session_id, workflow_yaml)
                        session.workflow_path = str(path)
                        session.workflow_ready = True
                        session.messages.append(
                            ConversationMessage(
                                role="assistant",
                                content="workflow.yamlの生成が完了しました。ダウンロードできます。",
                            )
                        )
            elif job.status == JobStatus.FAILED:
                if not session.workflow_ready:
                    error_message = job.steps[-1].message if job.steps else job.status
                    session.messages.append(
                        ConversationMessage(
                            role="assistant",
                            content=f"生成に失敗しました: {error_message}",
                        )
                    )

            self._sessions[session_id] = session

    # ------------------------------------------------------------------
    def _write_workflow_file(self, session_id: str, workflow_yaml: str) -> Path:
        session_dir = self._storage_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        workflow_path = session_dir / "workflow.yaml"
        workflow_path.write_text(workflow_yaml, encoding="utf-8")
        return workflow_path


conversation_manager = ConversationManager()
