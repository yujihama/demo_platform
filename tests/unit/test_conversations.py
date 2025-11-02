from __future__ import annotations

import asyncio
from fastapi import BackgroundTasks

from backend.app.models.conversation import ConversationStartRequest
from backend.app.services.conversations import ConversationManager
from backend.app.services.jobs import JobRegistry
from backend.app.services.pipeline import GenerationPipeline


def test_conversation_manager_generates_workflow(tmp_path) -> None:
    manager = ConversationManager(storage_root=tmp_path / "conversations")
    pipeline = GenerationPipeline(jobs=JobRegistry(), working_root=tmp_path / "work", output_root=tmp_path / "out")

    payload = ConversationStartRequest(
        user_id="tester",
        project_id="demo-project",
        project_name="デモアプリ",
        prompt="請求書からデータを抽出するアプリを作って"
    )

    background_tasks = BackgroundTasks()
    response = manager.start_conversation(payload, background_tasks, generation_pipeline=pipeline)

    # 実際のバックグラウンドタスクを同期的に実行
    asyncio.run(background_tasks())

    status = manager.get_session(response.session_id)
    assert status.workflow_ready is True
    assert status.status == "completed"

    workflow = manager.get_workflow(response.session_id)
    assert "info:" in workflow.workflow
    assert "pipeline:" in workflow.workflow

    stored_path = (tmp_path / "conversations" / response.session_id / "workflow.yaml")
    assert stored_path.exists()
