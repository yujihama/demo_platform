"""Storage service for conversation sessions and generated workflow.yaml files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ConversationStorage:
    """Thread-safe storage for conversation sessions and generated artifacts."""
    
    def __init__(self, storage_root: Path = Path("storage/conversations")) -> None:
        self._storage_root = storage_root
        self._storage_root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_prompt: str, user_id: str = "default") -> str:
        """Create a new conversation session."""
        session_id = str(uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt,
                    "timestamp": None,  # Will be set by caller if needed
                }
            ],
            "workflow_yaml": None,
            "status": "generating",
            "created_at": None,
            "updated_at": None,
        }
        
        with self._lock:
            self._sessions[session_id] = session_data
            self._save_session(session_id, session_data)
        
        logger.info("Created conversation session %s", session_id)
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data."""
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id].copy()
            
            # Try to load from disk
            session_file = self._storage_root / f"{session_id}.json"
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text(encoding="utf-8"))
                    self._sessions[session_id] = data
                    return data.copy()
                except Exception as e:
                    logger.error("Failed to load session %s: %s", session_id, e)
                    return None
        
        return None
    
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to the conversation."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                session_file = self._storage_root / f"{session_id}.json"
                if session_file.exists():
                    session = json.loads(session_file.read_text(encoding="utf-8"))
                    self._sessions[session_id] = session
                else:
                    logger.warning("Session %s not found", session_id)
                    return
            
            if "messages" not in session:
                session["messages"] = []
            
            session["messages"].append({
                "role": role,
                "content": content,
                "timestamp": None,
            })
            session["updated_at"] = None
            
            self._sessions[session_id] = session
            self._save_session(session_id, session)
    
    def save_workflow_yaml(self, session_id: str, workflow_yaml: str) -> None:
        """Save generated workflow.yaml for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                session_file = self._storage_root / f"{session_id}.json"
                if session_file.exists():
                    session = json.loads(session_file.read_text(encoding="utf-8"))
                    self._sessions[session_id] = session
                else:
                    logger.warning("Session %s not found", session_id)
                    return
            
            session["workflow_yaml"] = workflow_yaml
            session["status"] = "completed"
            session["updated_at"] = None
            
            # Save workflow.yaml file
            workflow_file = self._storage_root / f"{session_id}_workflow.yaml"
            workflow_file.write_text(workflow_yaml, encoding="utf-8")
            
            self._sessions[session_id] = session
            self._save_session(session_id, session)
            
            logger.info("Saved workflow.yaml for session %s", session_id)
    
    def get_workflow_yaml(self, session_id: str) -> Optional[str]:
        """Get workflow.yaml for a session."""
        session = self.get_session(session_id)
        if session and session.get("workflow_yaml"):
            return session["workflow_yaml"]
        
        # Try to load from disk
        workflow_file = self._storage_root / f"{session_id}_workflow.yaml"
        if workflow_file.exists():
            return workflow_file.read_text(encoding="utf-8")
        
        return None
    
    def update_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                session_file = self._storage_root / f"{session_id}.json"
                if session_file.exists():
                    session = json.loads(session_file.read_text(encoding="utf-8"))
                    self._sessions[session_id] = session
                else:
                    logger.warning("Session %s not found", session_id)
                    return
            
            session["status"] = status
            session["updated_at"] = None
            self._sessions[session_id] = session
            self._save_session(session_id, session)
    
    def _save_session(self, session_id: str, session_data: Dict[str, Any]) -> None:
        """Save session data to disk."""
        session_file = self._storage_root / f"{session_id}.json"
        try:
            session_file.write_text(
                json.dumps(session_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Failed to save session %s: %s", session_id, e)


# Singleton instance
conversation_storage = ConversationStorage()
