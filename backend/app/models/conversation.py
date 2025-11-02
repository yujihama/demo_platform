"""Pydantic models for conversational generation sessions."""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .generation import JobStatus, JobStep


RoleType = Literal["user", "assistant", "system"]


class ConversationMessage(BaseModel):
    """Represents a single message exchanged in the conversation."""

    role: RoleType = Field(description="Message sender role")
    content: str = Field(description="Message text content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationCreateRequest(BaseModel):
    """Request payload for starting a conversation-driven generation session."""

    user_id: str = Field(description="Identifier of the requesting user")
    project_id: str = Field(description="Project identifier for grouping outputs")
    project_name: str = Field(description="Display name of the generated project")
    prompt: str = Field(description="Natural language requirements provided by the user")
    description: Optional[str] = Field(
        default=None,
        description="Optional description used when packaging artifacts",
    )


class ConversationCreateResponse(BaseModel):
    """Response returned when a conversation session is created."""

    session_id: str = Field(description="Conversation session identifier")
    status: JobStatus = Field(description="Current job status")
    messages: List[ConversationMessage] = Field(default_factory=list)


class ConversationStatusResponse(BaseModel):
    """Status payload describing the current state of a conversation."""

    session_id: str = Field(description="Conversation session identifier")
    status: JobStatus = Field(description="Overall generation status")
    messages: List[ConversationMessage] = Field(default_factory=list)
    steps: List[JobStep] = Field(default_factory=list)
    download_url: Optional[str] = Field(default=None, description="Download URL if packaging is complete")


class WorkflowDocumentResponse(BaseModel):
    """Response returning the generated workflow.yaml content."""

    session_id: str = Field(description="Conversation session identifier")
    workflow_yaml: str = Field(description="Generated workflow.yaml content")
    updated_at: datetime = Field(description="Timestamp of the latest update")


class PackageResponse(BaseModel):
    """Metadata describing the downloadable package artifact."""

    session_id: str = Field(description="Conversation session identifier")
    filename: str = Field(description="Suggested filename for the package")
    size_bytes: int = Field(description="Size of the generated package in bytes")
    updated_at: datetime = Field(description="Timestamp when the package was produced")

