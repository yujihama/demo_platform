from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_create_conversation_and_fetch_workflow():
    response = client.post(
        "/api/generate/conversations",
        json={"prompt": "請求書からデータを抽出するアプリを作って"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    assert body["workflow_ready"] is True
    session_id = body["session_id"]

    workflow_response = client.get(f"/api/generate/conversations/{session_id}/workflow")
    assert workflow_response.status_code == 200
    assert "info:" in workflow_response.text

    package_response = client.post(f"/api/generate/conversations/{session_id}/package")
    assert package_response.status_code == 200
    assert package_response.headers["content-type"] == "application/zip"
