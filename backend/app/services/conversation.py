"""Service layer for orchestrating LLM conversations and workflow artifacts."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from ..models.conversation import (
    ConversationCreateRequest,
    ConversationMessage,
    ConversationRole,
    ConversationStatus,
)
from ..models.generation import GenerationRequest, GenerationOptions
from .pipeline import GenerationPipeline, WorkflowArtifact, pipeline


@dataclass
class ConversationSession:
    session_id: str
    status: ConversationStatus
    messages: list[ConversationMessage] = field(default_factory=list)
    workflow_path: Optional[Path] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_completed(self, workflow_path: Path, assistant_message: str) -> None:
        self.status = ConversationStatus.COMPLETED
        self.workflow_path = workflow_path
        self.messages.append(
            ConversationMessage(role=ConversationRole.ASSISTANT, content=assistant_message)
        )
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, error_message: str) -> None:
        self.status = ConversationStatus.FAILED
        self.error = error_message
        self.messages.append(
            ConversationMessage(role=ConversationRole.ASSISTANT, content=error_message)
        )
        self.updated_at = datetime.now(timezone.utc)


class ConversationService:
    """Coordinate prompt handling, pipeline execution, and workflow persistence."""

    def __init__(
        self,
        pipeline: GenerationPipeline,
        *,
        storage_root: Path | None = None,
    ) -> None:
        self._pipeline = pipeline
        self._storage_root = storage_root or Path("generated/conversations")
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    def create_session(self, payload: ConversationCreateRequest) -> ConversationSession:
        slug = self._slugify(payload.project_name or payload.prompt)
        project_id = slug or "generated-app"
        project_name = payload.project_name or self._title_case(project_id)
        user_id = payload.user_id or "demo-user"

        session_id = self._generate_session_id()
        session = ConversationSession(session_id=session_id, status=ConversationStatus.PROCESSING)
        session.messages.append(ConversationMessage(role=ConversationRole.USER, content=payload.prompt))

        with self._lock:
            self._sessions[session_id] = session

        request = GenerationRequest(
            user_id=user_id,
            project_id=project_id,
            project_name=project_name,
            description=payload.prompt,
            requirements_prompt=payload.prompt,
            use_mock=False,
            options=GenerationOptions(include_docker=False, include_logging=False, include_playwright=False),
        )

        try:
            artifact = self._pipeline.generate_workflow(request)
            workflow_path = self._persist_workflow(session_id, artifact)
            assistant_message = self._build_assistant_message(artifact)
            session.mark_completed(workflow_path, assistant_message)
        except Exception as exc:  # noqa: PERF203 - 明示的に失敗を捕捉
            session.mark_failed(f"workflow.yaml の生成に失敗しました: {exc}")

        return session

    # ------------------------------------------------------------------
    def get_session(self, session_id: str) -> ConversationSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    # ------------------------------------------------------------------
    def require_session(self, session_id: str) -> ConversationSession:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(session_id)
        return session

    # ------------------------------------------------------------------
    def _persist_workflow(self, session_id: str, artifact: WorkflowArtifact) -> Path:
        session_dir = self._storage_root / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        workflow_path = session_dir / "workflow.yaml"
        workflow_path.write_text(artifact.yaml_text, encoding="utf-8")

        metadata_path = session_dir / "metadata.json"
        metadata_path.write_text(artifact.metadata_json, encoding="utf-8")
        return workflow_path

    # ------------------------------------------------------------------
    @staticmethod
    def _build_assistant_message(artifact: WorkflowArtifact) -> str:
        info = artifact.workflow.get("info", {})
        name = info.get("name") or "生成されたアプリケーション"
        description = info.get("description") or "workflow.yaml が生成されました。"
        return f"{name} の workflow.yaml を作成しました。\n{description}"

    # ------------------------------------------------------------------
    @staticmethod
    def _slugify(value: str) -> str:
        import re

        cleaned = re.sub(r"[^0-9a-zA-Z]+", "-", value)
        cleaned = cleaned.strip("-").lower()
        return cleaned

    # ------------------------------------------------------------------
    @staticmethod
    def _title_case(value: str) -> str:
        parts = [part.capitalize() for part in value.split("-") if part]
        return " ".join(parts) or "Generated App"

    # ------------------------------------------------------------------
    @staticmethod
    def _generate_session_id() -> str:
        from uuid import uuid4

        return str(uuid4())


conversation_service = ConversationService(pipeline=pipeline)

