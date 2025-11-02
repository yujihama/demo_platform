"""Service layer for orchestrating LLM conversations that produce workflow.yaml."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import BackgroundTasks

from ..models.conversation import (
    ConversationCreateRequest,
    ConversationMessage,
    ConversationSessionResponse,
    ConversationStatus,
)
from .workflow_generation import WorkflowGenerator
from .workflow_packaging import WorkflowPackagingService

logger = logging.getLogger(__name__)


@dataclass
class _ConversationRecord:
    session_id: str
    request: ConversationCreateRequest
    status: ConversationStatus = ConversationStatus.RUNNING
    messages: List[ConversationMessage] = field(default_factory=list)
    workflow_yaml: Optional[str] = None
    metadata: Optional[Dict[str, object]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_response(self) -> ConversationSessionResponse:
        return ConversationSessionResponse(
            session_id=self.session_id,
            status=self.status,
            messages=list(self.messages),
            workflow_yaml=self.workflow_yaml,
            metadata=self.metadata,
            error=self.error,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class ConversationService:
    """Manage conversation sessions and delegate workflow generation."""

    def __init__(
        self,
        *,
        generator: WorkflowGenerator | None = None,
        storage_dir: Path | None = None,
        packaging: WorkflowPackagingService | None = None,
    ) -> None:
        self._generator = generator or WorkflowGenerator()
        self._storage_dir = storage_dir or Path("generated/conversations")
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._packaging = packaging or WorkflowPackagingService(Path("output"))
        self._records: Dict[str, _ConversationRecord] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    def start(
        self,
        request: ConversationCreateRequest,
        background_tasks: BackgroundTasks,
    ) -> ConversationSessionResponse:
        session_id = str(uuid4())
        message = ConversationMessage(role="user", content=request.prompt)
        system_message = ConversationMessage(
            role="assistant",
            content="要件を受け付けました。workflow.yamlの生成を開始します。",
        )
        record = _ConversationRecord(
            session_id=session_id,
            request=request,
            status=ConversationStatus.RUNNING,
            messages=[message, system_message],
        )
        with self._lock:
            self._records[session_id] = record

        background_tasks.add_task(self._generate_workflow, session_id)
        logger.info("Conversation session %s started", session_id)
        return record.to_response()

    # ------------------------------------------------------------------
    def get(self, session_id: str) -> ConversationSessionResponse:
        with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise KeyError(f"Conversation session {session_id} not found")
            return record.to_response()

    # ------------------------------------------------------------------
    def get_workflow_yaml(self, session_id: str) -> str:
        with self._lock:
            record = self._records.get(session_id)
            if record is None or record.workflow_yaml is None:
                raise KeyError(f"workflow.yaml not ready for session {session_id}")
            return record.workflow_yaml

    # ------------------------------------------------------------------
    def package(self, session_id: str) -> Path:
        with self._lock:
            record = self._records.get(session_id)
            if record is None:
                raise KeyError(f"Conversation session {session_id} not found")
            if record.workflow_yaml is None:
                raise ValueError("workflow.yaml is not ready yet")

            metadata = record.metadata or {}
            metadata.setdefault("conversation", {})
            metadata["conversation"]["messages"] = [
                {
                    "role": message.role,
                    "content": message.content,
                    "created_at": message.created_at.isoformat(),
                }
                for message in record.messages
            ]

            zip_path = self._packaging.package_conversation(
                session_id=session_id,
                user_id=record.request.user_id,
                project_id=record.request.project_id,
                project_name=record.request.project_name,
                description=record.request.prompt,
                workflow_yaml=record.workflow_yaml,
                metadata=metadata,
            )
            return zip_path

    # ------------------------------------------------------------------
    def _generate_workflow(self, session_id: str) -> None:
        try:
            with self._lock:
                record = self._records.get(session_id)
                if record is None:
                    logger.warning("Session %s missing during generation", session_id)
                    return
                request = record.request

            result = self._generator.generate(
                request.prompt,
            )

            validation_metadata = dict(result.validation)
            validation_model = validation_metadata.get("model")
            if validation_model is not None and hasattr(validation_model, "model_dump"):
                validation_metadata["model"] = validation_model.model_dump()

            metadata = {
                "analysis": result.analysis.model_dump() if hasattr(result.analysis, "model_dump") else result.analysis,
                "architecture": result.architecture.model_dump() if hasattr(result.architecture, "model_dump") else result.architecture,
                "validation": validation_metadata,
            }

            workflow_dir = self._storage_dir / session_id
            workflow_dir.mkdir(parents=True, exist_ok=True)
            workflow_path = workflow_dir / "workflow.yaml"
            workflow_path.write_text(result.yaml_content, encoding="utf-8")
            metadata_path = workflow_dir / "metadata.json"
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with self._lock:
                record = self._records.get(session_id)
                if record is None:
                    return
                record.status = ConversationStatus.COMPLETED
                record.workflow_yaml = result.yaml_content
                record.metadata = metadata
                record.updated_at = datetime.utcnow()
                record.messages.append(
                    ConversationMessage(
                        role="assistant",
                        content="workflow.yamlの生成が完了しました。プレビューとダウンロードが可能です。",
                    )
                )

            logger.info("Conversation session %s completed", session_id)

        except Exception as exc:  # noqa: PERF203
            logger.exception("Conversation session %s failed", session_id)
            with self._lock:
                record = self._records.get(session_id)
                if record is None:
                    return
                record.status = ConversationStatus.FAILED
                record.error = str(exc)
                record.updated_at = datetime.utcnow()
                record.messages.append(
                    ConversationMessage(
                        role="assistant",
                        content=f"workflow.yamlの生成に失敗しました: {exc}",
                    )
                )


conversation_service = ConversationService()

