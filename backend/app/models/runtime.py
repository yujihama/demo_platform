"""Pydantic models for workflow runtime API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .workflow import WorkflowYaml


class WorkflowAppResponse(BaseModel):
    workflow: WorkflowYaml


class SessionCreateResponse(BaseModel):
    session_id: str
    status: str
    current_step: Optional[str] = None
    view: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class SessionExecuteRequest(BaseModel):
    step_id: Optional[str] = Field(default=None, description="Identifier of the UI step triggering execution")
    inputs: Dict[str, Any] = Field(default_factory=dict)


class WorkflowSessionResponse(BaseModel):
    session_id: str
    status: str
    current_step: Optional[str] = None
    view: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
