from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.playwright
def test_workflow_generation_success(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("ユーザー ID").fill("ui-llm-user")
    page.get_by_label("プロジェクト ID").fill("ui-llm-project")
    page.get_by_label("プロジェクト名").fill("UI LLM Integration Test")
    page.get_by_label("プロジェクト概要").fill("Playwright から生成したプロジェクト")
    page.get_by_label("要件プロンプト").fill(
        "force retry Build an invoice validation assistant that retries on the first validation attempt"
    )

    page.get_by_role("button", name="ワークフロー生成").click()

    page.get_by_test_id("chat-messages").get_by_text("Analyst Agent").wait_for(timeout=20000)
    page.get_by_text("検証成功").wait_for(timeout=20000)

    yaml_preview = page.get_by_test_id("yaml-preview")
    yaml_preview.wait_for(timeout=20000)

    download_button = page.get_by_role("button", name="ZIP をダウンロード")
    download_button.wait_for(timeout=20000)
    assert download_button.is_enabled()
    href = download_button.get_attribute("href")
    assert href and href.endswith("/download")


@pytest.mark.playwright
def test_workflow_generation_failure(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("要件プロンプト").fill(
        "force failure Build a validation assistant that should fail for testing error handling"
    )

    page.get_by_role("button", name="ワークフロー生成").click()

    alert = page.get_by_role("alert")
    alert.wait_for(timeout=20000)
    text = alert.inner_text()
    assert "検証" in text or "YAML" in text
    download_button = page.get_by_role("button", name="ZIP をダウンロード")
    assert download_button.is_disabled()

