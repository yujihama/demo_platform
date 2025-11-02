"""Pydantic models for LLM conversation orchestration."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationCreateRequest(BaseModel):
    user_id: str = Field(..., description="ユーザー識別子")
    project_id: str = Field(..., description="プロジェクト識別子")
    project_name: str = Field(..., description="生成するアプリの名称")
    prompt: str = Field(..., description="LLMに渡す要件プロンプト")


class ConversationMessage(BaseModel):
    role: str = Field(..., description="messageの役割: user/assistant/system")
    content: str = Field(..., description="メッセージ本文")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationSessionResponse(BaseModel):
    session_id: str
    status: ConversationStatus
    messages: List[ConversationMessage]
    workflow_yaml: Optional[str] = None
    metadata: Optional[Dict[str, object]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

