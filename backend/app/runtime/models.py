"""Pydantic models for runtime API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ComponentState(BaseModel):
    """State tracked for each UI component."""

    value: Any = None
    status: str = Field(default="idle")
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    """Runtime session state persisted in the store."""

    session_id: str
    context: Dict[str, Any] = Field(default_factory=dict)
    component_state: Dict[str, ComponentState] = Field(default_factory=dict)
    next_step_index: int = 0
    status: str = Field(default="idle")
    active_step_id: Optional[str] = None
    waiting_for: List[str] = Field(default_factory=list)
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionCreateResponse(BaseModel):
    """Response payload when a session is created."""

    session: SessionState
    workflow: Dict[str, Any]


class SessionActionResponse(BaseModel):
    """Response payload after executing a session action."""

    session: SessionState


class ComponentValueUpdate(BaseModel):
    """Payload for updating component values."""

    value: Any


class AdvanceRequest(BaseModel):
    """Optional payload for advance actions."""

    step_id: Optional[str] = None


