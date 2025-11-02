"""In-memory store for managing conversation-driven generation sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, Iterable, Optional

from ..models.conversation import ConversationMessage
from ..models.generation import JobStatus


@dataclass
class ConversationSession:
    """Represents state stored for each conversational generation session."""

    session_id: str
    user_id: str
    project_id: str
    project_name: str
    prompt: str
    status: JobStatus
    messages: list[ConversationMessage]
    created_at: datetime
    updated_at: datetime
    workflow_path: Optional[Path] = None
    package_path: Optional[Path] = None
    metadata_path: Optional[Path] = None


class ConversationSessionManager:
    """Thread-safe manager that persists conversation sessions to the filesystem."""

    def __init__(self, storage_root: Path | str = Path("generated/conversations")) -> None:
        self._storage_root = Path(storage_root)
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = Lock()

    def create_session(
        self,
        session_id: str,
        user_id: str,
        project_id: str,
        project_name: str,
        prompt: str,
    ) -> ConversationSession:
        now = datetime.utcnow()
        message = ConversationMessage(role="user", content=prompt, timestamp=now)
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            project_id=project_id,
            project_name=project_name,
            prompt=prompt,
            status=JobStatus.RECEIVED,
            messages=[message],
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return ConversationSession(
                session_id=session.session_id,
                user_id=session.user_id,
                project_id=session.project_id,
                project_name=session.project_name,
                prompt=session.prompt,
                status=session.status,
                messages=list(session.messages),
                created_at=session.created_at,
                updated_at=session.updated_at,
                workflow_path=session.workflow_path,
                package_path=session.package_path,
                metadata_path=session.metadata_path,
            )

    def list_sessions(self) -> Iterable[ConversationSession]:
        with self._lock:
            for session in self._sessions.values():
                yield ConversationSession(
                    session_id=session.session_id,
                    user_id=session.user_id,
                    project_id=session.project_id,
                    project_name=session.project_name,
                    prompt=session.prompt,
                    status=session.status,
                    messages=list(session.messages),
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    workflow_path=session.workflow_path,
                    package_path=session.package_path,
                    metadata_path=session.metadata_path,
                )

    def complete_session(
        self,
        session_id: str,
        workflow_yaml: str,
        package_path: Path,
        metadata_path: Optional[Path] = None,
    ) -> None:
        assistant_message = ConversationMessage(
            role="assistant",
            content="workflow.yaml の生成が完了しました。パッケージをダウンロードできます。",
        )
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session.status = JobStatus.COMPLETED
            session.messages.append(assistant_message)
            session.updated_at = datetime.utcnow()

            session_dir = self._storage_root / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            workflow_path = session_dir / "workflow.yaml"
            workflow_path.write_text(workflow_yaml, encoding="utf-8")

            session.workflow_path = workflow_path
            session.package_path = package_path
            session.metadata_path = metadata_path

    def fail_session(self, session_id: str, error_message: str) -> None:
        failure_message = ConversationMessage(role="assistant", content=error_message)
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session.status = JobStatus.FAILED
            session.messages.append(failure_message)
            session.updated_at = datetime.utcnow()

    def update_progress(self, session_id: str, status: JobStatus, message: str | None = None) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return
            session.status = status
            session.updated_at = datetime.utcnow()
            if message:
                session.messages.append(
                    ConversationMessage(role="system", content=message, timestamp=datetime.utcnow())
                )


conversation_sessions = ConversationSessionManager()

