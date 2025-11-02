from __future__ import annotations

import json
import zipfile
from pathlib import Path

from fastapi import BackgroundTasks

from backend.app.models.conversation import ConversationCreateRequest, ConversationStatus
from backend.app.services.conversation import ConversationService
from backend.app.services.workflow_generation import WorkflowGenerationResult
from backend.app.services.workflow_packaging import WorkflowPackagingService


class _DummyModel:
    def __init__(self, data: dict) -> None:
        self._data = data

    def model_dump(self) -> dict:
        return dict(self._data)


class _DummyGenerator:
    def __init__(self) -> None:
        self.result = WorkflowGenerationResult(
            yaml_content="info: demo\n",
            analysis=_DummyModel({"summary": "analysis"}),
            architecture=_DummyModel({"layout": "architecture"}),
            validation={"valid": True, "model": _DummyModel({"status": "ok"})},
        )

    def generate(self, prompt: str, **callbacks):  # type: ignore[override]
        if callback := callbacks.get("on_analysis"):
            callback(self.result.analysis)
        if callback := callbacks.get("on_architecture"):
            callback(self.result.architecture)
        if callback := callbacks.get("on_yaml"):
            callback(self.result.yaml_content)
        if callback := callbacks.get("on_validation"):
            callback(self.result.validation)
        return self.result


def _read_metadata(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_conversation_service_generates_and_packages(tmp_path: Path) -> None:
    storage = tmp_path / "sessions"
    output = tmp_path / "output"
    service = ConversationService(
        generator=_DummyGenerator(),
        storage_dir=storage,
        packaging=WorkflowPackagingService(output),
    )

    request = ConversationCreateRequest(
        user_id="demo-user",
        project_id="demo-project",
        project_name="デモアプリ",
        prompt="請求書からデータを抽出するアプリを作って",
    )

    initial = service.start(request, BackgroundTasks())
    assert initial.status == ConversationStatus.RUNNING

    service._generate_workflow(initial.session_id)

    session = service.get(initial.session_id)
    assert session.status == ConversationStatus.COMPLETED
    assert session.workflow_yaml is not None and "info: demo" in session.workflow_yaml
    assert session.metadata is not None

    workflow_path = storage / initial.session_id / "workflow.yaml"
    assert workflow_path.exists()
    assert workflow_path.read_text(encoding="utf-8").startswith("info: demo")

    metadata_path = storage / initial.session_id / "metadata.json"
    metadata = _read_metadata(metadata_path)
    assert metadata["analysis"]["summary"] == "analysis"

    package_path = service.package(initial.session_id)
    assert package_path.exists()

    with zipfile.ZipFile(package_path, "r") as archive:
        contents = sorted(archive.namelist())
        assert contents == [".env.example", "README.md", "docker-compose.yml", "workflow.yaml"]

