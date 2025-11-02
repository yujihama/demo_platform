"""Pydantic models for LLM conversation workflow generation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ConversationRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    role: ConversationRole
    content: str


class ConversationStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationCreateRequest(BaseModel):
    prompt: str = Field(..., description="ユーザーからの初回プロンプト。")
    project_name: str | None = Field(
        default=None,
        description="生成されるアプリケーションの表示名。指定がない場合はプロンプトから推測する。",
    )
    user_id: str | None = Field(
        default=None,
        description="セッションに関連付けるユーザーID。省略時はデフォルト値を利用する。",
    )


class ConversationCreateResponse(BaseModel):
    session_id: str
    status: ConversationStatus
    messages: List[ConversationMessage]
    workflow_ready: bool = Field(
        False, description="workflow.yaml が利用可能な状態かどうかを示すフラグ"
    )


class ConversationStatusResponse(BaseModel):
    session_id: str
    status: ConversationStatus
    messages: List[ConversationMessage]
    workflow_ready: bool
    created_at: datetime
    updated_at: datetime
    error: Optional[str] = None

