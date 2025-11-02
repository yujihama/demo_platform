import base64
from pathlib import Path

import httpx
import pytest
import yaml

from backend.app.workflow_runtime.service import WorkflowRuntimeService
from backend.app.workflow_runtime.storage import InMemorySessionStore


@pytest.fixture()
def sample_workflow(tmp_path: Path) -> Path:
    workflow = {
        "info": {
            "name": "テストワークフロー",
            "description": "ユニットテスト用のワークフロー",
            "version": "1.0.0",
        },
        "workflows": {
            "sample": {
                "provider": "mock",
                "endpoint": "http://mock/workflow",
            }
        },
        "ui": {
            "layout": "wizard",
            "steps": []
        },
        "pipeline": {
            "steps": [
                {
                    "id": "store_file",
                    "component": "file_uploader",
                    "params": {
                        "input_id": "upload",
                        "target": "inputs.upload"
                    },
                },
                {
                    "id": "call_api",
                    "component": "call_workflow",
                    "params": {
                        "workflow": "sample",
                        "input_mapping": {
                            "document": "$inputs.upload"
                        },
                        "output_path": "steps.call_api.response",
                    },
                },
                {
                    "id": "transform",
                    "component": "for_each",
                    "params": {
                        "source": "steps.call_api.response.outputs.items",
                        "target": "view.results.items",
                        "view_path": "view.results.items",
                        "map": {
                            "field": "{{ item.field }}",
                            "status": "{{ item.status }}",
                        },
                    },
                },
            ]
        },
    }
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(yaml.safe_dump(workflow, allow_unicode=True), encoding="utf-8")
    return workflow_path


@pytest.fixture()
def mock_http_client() -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "workflow_run_id": "test-run",
                "workflow_id": "sample",
                "status": "succeeded",
                "outputs": {
                    "items": [
                        {"field": "document", "status": "ok"},
                    ]
                },
            },
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        yield client


def test_workflow_runtime_executes_pipeline(sample_workflow: Path, mock_http_client: httpx.Client) -> None:
    service = WorkflowRuntimeService(sample_workflow, InMemorySessionStore(), http_client=mock_http_client)
    session = service.create_session()

    payload = {
        "upload": {
            "name": "invoice.pdf",
            "content_type": "application/pdf",
            "content": base64.b64encode(b"data").decode("utf-8"),
        }
    }

    result = service.execute_session(session.session_id, payload, step_id="upload_step")

    assert result.status == "completed"
    assert result.view["results"] == {
        "items": [
            {"field": "document", "status": "ok"}
        ]
    }
    stored_file = result.data["inputs"]["upload"]
    assert stored_file["name"] == "invoice.pdf"
    assert stored_file["size"] == len(b"data")

    service.close()
