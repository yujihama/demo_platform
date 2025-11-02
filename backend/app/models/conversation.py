"""LLM対話セッション用のPydanticモデル。"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from .generation import GenerationRequest, GenerationOptions, JobStatus


class ConversationStartRequest(BaseModel):
    """チャットセッション開始時のリクエスト。"""

    user_id: str = Field(..., description="ユーザーID")
    project_id: str = Field(..., description="プロジェクトID")
    project_name: str = Field(..., description="プロジェクト名")
    prompt: str = Field(..., description="LLMへの初回プロンプト")
    description: Optional[str] = Field(
        default=None,
        description="プロジェクトの概要。指定しない場合はpromptを利用する",
    )

    def to_generation_request(self) -> GenerationRequest:
        """GenerationRequestへ変換する。"""

        base_description = self.description or self.prompt
        return GenerationRequest(
            user_id=self.user_id,
            project_id=self.project_id,
            project_name=self.project_name,
            description=base_description,
            requirements_prompt=self.prompt,
            mock_spec_id="invoice-verification",
            options=GenerationOptions(),
            use_mock=False,
        )


class ConversationMessage(BaseModel):
    """チャット内のメッセージ表現。"""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationSession(BaseModel):
    """バックエンドで保持するセッション情報。"""

    session_id: str
    job_id: str
    status: JobStatus
    messages: List[ConversationMessage] = Field(default_factory=list)
    workflow_ready: bool = False
    download_url: Optional[str] = None
    workflow_path: Optional[str] = None


class ConversationStartResponse(BaseModel):
    """セッション開始時のレスポンス。"""

    session_id: str
    job_id: str
    status: JobStatus
    messages: List[ConversationMessage]


class ConversationStatusResponse(BaseModel):
    """セッション状態取得レスポンス。"""

    session_id: str
    job_id: str
    status: JobStatus
    messages: List[ConversationMessage]
    workflow_ready: bool
    download_url: Optional[str] = None


class WorkflowContentResponse(BaseModel):
    """生成されたworkflow.yamlの内容。"""

    workflow: str
