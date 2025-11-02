"""Pydantic models for workflow runtime API."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .workflow import WorkflowYaml


class StepStateModel(BaseModel):
    status: str
    output: Optional[Any] = None
    error: Optional[str] = None


class SessionStateModel(BaseModel):
    session_id: str = Field(..., description="Active session identifier")
    inputs: Dict[str, Any] = Field(default_factory=dict)
    data: Dict[str, Any] = Field(default_factory=dict)
    steps: Dict[str, StepStateModel] = Field(default_factory=dict)


class WorkflowDefinitionResponse(BaseModel):
    workflow: WorkflowYaml


class SessionCreateResponse(BaseModel):
    session: SessionStateModel


class SessionStateResponse(BaseModel):
    session: SessionStateModel


class ExecuteResponse(BaseModel):
    session: SessionStateModel


class ErrorResponse(BaseModel):
    detail: str
