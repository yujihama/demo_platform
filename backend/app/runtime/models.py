"""Data models used by the workflow runtime engine."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field

StepStatusLiteral = Literal["pending", "running", "completed", "error"]
SessionStatusLiteral = Literal["awaiting_input", "processing", "completed", "error"]


class SessionContext(BaseModel):
    """Container holding public and private context data."""

    public: Dict[str, Any] = Field(default_factory=dict)
    private: Dict[str, Any] = Field(default_factory=dict)

    def merged(self) -> Dict[str, Any]:
        """Return a merged view of public and private data."""

        data: Dict[str, Any] = {}
        data.update(self.private)
        data.update(self.public)
        return data


class WorkflowSession(BaseModel):
    """Complete runtime session state persisted in Redis."""

    session_id: str
    workflow_id: str
    status: SessionStatusLiteral = "awaiting_input"
    active_ui_step: Optional[str] = None
    completed_ui_steps: List[str] = Field(default_factory=list)
    step_status: Dict[str, StepStatusLiteral] = Field(default_factory=dict)
    context: SessionContext = Field(default_factory=SessionContext)
    step_outputs: Dict[str, Any] = Field(default_factory=dict)
    last_error: Optional[str] = None
    pipeline_index: int = -1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def touch(self) -> None:
        """Update the `updated_at` timestamp."""

        self.updated_at = datetime.utcnow()

    def to_public_state(self) -> "WorkflowSessionPublicState":
        """Serialize the session for frontend consumption."""

        return WorkflowSessionPublicState(
            session_id=self.session_id,
            workflow_id=self.workflow_id,
            status=self.status,
            active_ui_step=self.active_ui_step,
            completed_ui_steps=list(self.completed_ui_steps),
            step_status=dict(self.step_status),
            context=dict(self.context.public),
            last_error=self.last_error,
            updated_at=self.updated_at,
        )


class WorkflowSessionPublicState(BaseModel):
    """Subset of session state returned to the frontend."""

    session_id: str
    workflow_id: str
    status: SessionStatusLiteral
    active_ui_step: Optional[str]
    completed_ui_steps: List[str] = Field(default_factory=list)
    step_status: Dict[str, StepStatusLiteral] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    last_error: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SubmitStepPayload(BaseModel):
    """Request payload for JSON-based step submissions."""

    data: Dict[str, Any] = Field(default_factory=dict)
    component_id: Optional[str] = None
