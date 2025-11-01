from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.playwright
def test_ui_wizard_mock_mode_happy_path(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("アプリケーション要件 / プロンプト").fill("Generate a mock invoice assistant for regression testing")
    page.get_by_label("ユーザー ID").fill("ui-user")
    page.get_by_label("プロジェクト ID").fill("ui-project")
    page.get_by_label("プロジェクト名").fill("UI Integration Test")

    page.get_by_role("button", name="workflow.yaml を生成").click()

    page.get_by_text("進捗").wait_for(timeout=10000)

    download_button = page.get_by_role("button", name="app.zip をダウンロード")
    download_button.wait_for(timeout=20000)
    href = download_button.get_attribute("href")
    assert href and href.endswith("/download")


@pytest.mark.playwright
def test_ui_wizard_llm_mode_happy_path(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("アプリケーション要件 / プロンプト").fill(
        "force retry Build an invoice validation assistant that retries on the first validation attempt"
    )
    page.get_by_role("switch", name="モックワークフローを使用").click()
    page.get_by_label("ユーザー ID").fill("ui-llm-user")
    page.get_by_label("プロジェクト ID").fill("ui-llm-project")
    page.get_by_label("プロジェクト名").fill("UI LLM Integration Test")

    page.get_by_role("button", name="workflow.yaml を生成").click()

    page.get_by_text("進捗").wait_for(timeout=15000)
    page.get_by_text("workflow.yaml の生成").wait_for(timeout=15000)

    download_button = page.get_by_role("button", name="app.zip をダウンロード")
    download_button.wait_for(timeout=25000)
    href = download_button.get_attribute("href")
    assert href and href.endswith("/download")


@pytest.mark.playwright
def test_ui_wizard_llm_validation_error(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("アプリケーション要件 / プロンプト").fill(
        "force failure Build a validation assistant that should fail for testing error handling"
    )
    page.get_by_role("switch", name="モックワークフローを使用").click()
    page.get_by_label("ユーザー ID").fill("ui-llm-error")
    page.get_by_label("プロジェクト ID").fill("ui-llm-error-project")
    page.get_by_label("プロジェクト名").fill("UI LLM Error Test")

    page.get_by_role("button", name="workflow.yaml を生成").click()

    alert = page.get_by_role("alert")
    alert.wait_for(timeout=20000)
    text = alert.inner_text()
    assert "workflow.yaml" in text
    assert "force failure" in text

