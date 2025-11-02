"""Workflow session models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class WorkflowSession:
    """Persisted session state for workflow execution."""

    session_id: str
    status: str = "idle"
    data: Dict[str, Any] = field(default_factory=dict)
    view: Dict[str, Any] = field(default_factory=dict)
    current_step: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def mark_running(self, step_id: Optional[str] = None) -> None:
        self.status = "running"
        self.current_step = step_id
        self.error = None
        self.updated_at = datetime.now(timezone.utc)

    def mark_completed(self) -> None:
        self.status = "completed"
        self.updated_at = datetime.now(timezone.utc)

    def mark_failed(self, message: str) -> None:
        self.status = "failed"
        self.error = message
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "data": self.data,
            "view": self.view,
            "current_step": self.current_step,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorkflowSession":
        data = dict(payload)
        for field_name in ("created_at", "updated_at"):
            value = data.get(field_name)
            if isinstance(value, str):
                data[field_name] = datetime.fromisoformat(value)
        return cls(**data)
