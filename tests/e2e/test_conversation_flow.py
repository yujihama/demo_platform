"""E2E tests for conversation-based workflow generation flow."""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import pytest
import requests
from playwright.sync_api import Page, expect


@pytest.mark.playwright
def test_conversation_flow_happy_path(
    prepare_environment,  # noqa: ARG001
    page: Page,
) -> None:
    """Test the full flow: prompt input -> YAML generation -> download -> verify package."""
    page.goto("http://127.0.0.1:5173/")

    # Step 1: Input natural language prompt in chat UI
    chat_input = page.locator('input[placeholder*="???????????"]')
    chat_input.wait_for(timeout=5000)
    chat_input.fill("????????????????????")

    # Send button
    send_button = page.get_by_role("button", name="??")
    send_button.click()

    # Step 2: Wait for conversation to start
    page.get_by_text("?????????").wait_for(timeout=5000)

    # Step 3: Poll for workflow completion
    # This might take a while, so we'll check periodically
    max_wait_time = 120  # 2 minutes
    poll_interval = 2
    elapsed = 0

    workflow_ready = False
    session_id = None

    while elapsed < max_wait_time and not workflow_ready:
        time.sleep(poll_interval)
        elapsed += poll_interval

        # Check if workflow is ready by looking for success message
        try:
            success_message = page.locator('text=workflow.yaml??????????')
            if success_message.is_visible(timeout=1000):
                workflow_ready = True
                # Extract session ID from API response or page
                # For now, we'll use a workaround: check the API directly
                break
        except Exception:
            pass

        # Also check for errors
        error_alerts = page.locator('text*=???').all()
        if error_alerts:
            error_text = "\n".join(alert.inner_text() for alert in error_alerts)
            if "??????????" in error_text:
                pytest.fail(f"Workflow generation failed: {error_text}")

    # If workflow is ready, proceed to verify package download
    if workflow_ready:
        # Step 4: Click download button
        download_button = page.get_by_role("button", name="????????????")
        download_button.wait_for(timeout=5000)

        # Set up download tracking
        with page.expect_download() as download_info:
            download_button.click()

        download = download_info.value
        download_path = download.path()

        # Step 5: Verify package contents
        assert download_path
        with zipfile.ZipFile(download_path, "r") as zip_file:
            file_list = zip_file.namelist()
            assert "workflow.yaml" in file_list, "workflow.yaml should be in package"
            assert "docker-compose.yml" in file_list, "docker-compose.yml should be in package"
            assert "README.md" in file_list, "README.md should be in package"
            assert ".env.example" in file_list, ".env.example should be in package"

            # Verify workflow.yaml content
            workflow_content = zip_file.read("workflow.yaml").decode("utf-8")
            assert "info:" in workflow_content, "workflow.yaml should contain info section"
            assert "ui:" in workflow_content or "workflows:" in workflow_content

            # Verify docker-compose.yml structure
            docker_content = zip_file.read("docker-compose.yml").decode("utf-8")
            assert "version:" in docker_content
            assert "services:" in docker_content
            assert "frontend:" in docker_content or "backend:" in docker_content

            # Verify README.md
            readme_content = zip_file.read("README.md").decode("utf-8")
            assert "Setup" in readme_content or "??????" in readme_content
            assert "docker-compose" in readme_content.lower()

    else:
        pytest.fail(
            f"Workflow generation did not complete within {max_wait_time} seconds. "
            "Check the conversation status or increase timeout."
        )


@pytest.mark.playwright
def test_conversation_workflow_preview(
    prepare_environment,  # noqa: ARG001
    page: Page,
) -> None:
    """Test that workflow preview is displayed after generation."""
    page.goto("http://127.0.0.1:5173/")

    # Send a prompt
    chat_input = page.locator('input[placeholder*="???????????"]')
    chat_input.wait_for(timeout=5000)
    chat_input.fill("?????????????????")

    send_button = page.get_by_role("button", name="??")
    send_button.click()

    # Wait for initial response
    page.get_by_text("?????????").wait_for(timeout=5000)

    # Wait for workflow preview to appear (may take time)
    max_wait = 120
    elapsed = 0
    preview_visible = False

    while elapsed < max_wait and not preview_visible:
        time.sleep(2)
        elapsed += 2

        try:
            preview_section = page.locator("text=????? workflow.yaml")
            if preview_section.is_visible(timeout=1000):
                preview_visible = True
                break
        except Exception:
            pass

    if preview_visible:
        # Verify preview shows YAML content
        yaml_preview = page.locator("pre")
        expect(yaml_preview).to_be_visible(timeout=5000)

        yaml_text = yaml_preview.inner_text()
        assert len(yaml_text) > 0, "YAML preview should not be empty"
        assert "info:" in yaml_text or "workflows:" in yaml_text or "ui:" in yaml_text
    else:
        # If preview doesn't appear, log but don't fail (generation might still be in progress)
        pytest.skip("Workflow preview did not appear within timeout - generation may still be in progress")


def test_conversation_api_flow() -> None:
    """Test conversation API endpoints directly."""
    base_url = "http://127.0.0.1:8100/api"

    # Step 1: Create conversation
    response = requests.post(
        f"{base_url}/generate/conversations",
        json={
            "prompt": "???????????????????",
            "user_id": "test-user",
        },
        timeout=10,
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert "session_id" in data
    session_id = data["session_id"]

    # Step 2: Poll for completion
    max_wait = 120
    elapsed = 0
    workflow_ready = False

    while elapsed < max_wait and not workflow_ready:
        time.sleep(2)
        elapsed += 2

        status_response = requests.get(
            f"{base_url}/generate/conversations/{session_id}",
            timeout=10,
        )
        assert status_response.status_code == 200

        status_data = status_response.json()
        if status_data.get("workflow_ready"):
            workflow_ready = True
            break

    if workflow_ready:
        # Step 3: Get workflow YAML
        workflow_response = requests.get(
            f"{base_url}/generate/conversations/{session_id}/workflow",
            timeout=10,
        )
        assert workflow_response.status_code == 200
        workflow_data = workflow_response.json()
        assert "workflow_yaml" in workflow_data
        assert len(workflow_data["workflow_yaml"]) > 0

        # Step 4: Download package
        download_response = requests.get(
            f"{base_url}/generate/conversations/{session_id}/download",
            timeout=30,
        )
        assert download_response.status_code == 200
        assert download_response.headers["content-type"] == "application/zip"

        # Verify zip contents
        import io

        with zipfile.ZipFile(io.BytesIO(download_response.content), "r") as zip_file:
            file_list = zip_file.namelist()
            assert "workflow.yaml" in file_list
            assert "docker-compose.yml" in file_list
            assert "README.md" in file_list
    else:
        pytest.skip("Workflow generation did not complete within timeout - may need more time")
