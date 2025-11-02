from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.playwright
def test_ui_wizard_mock_mode_happy_path(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("要件プロンプト").fill("Generate a mock invoice assistant for regression testing")
    page.get_by_label("ユーザー ID").fill("ui-user")
    page.get_by_label("プロジェクト ID").fill("ui-project")
    page.get_by_label("プロジェクト名").fill("UI Integration Test")
    page.get_by_label("プロジェクト概要").fill("UI フローの自動テストから生成されたプロジェクト")

    page.get_by_role("button", name="生成を開始").click()

    page.get_by_text("生成進捗").wait_for(timeout=10000)

    page.get_by_role("tab", name="3. モックプレビュー").click()
    page.get_by_role("button", name="承認して進む").wait_for(timeout=10000)
    page.get_by_role("button", name="承認して進む").click()

    page.get_by_role("tab", name="7. 成果物ダウンロード").click()
    download_button = page.get_by_role("button", name="ZIP をダウンロード")
    download_button.wait_for(timeout=20000)

    href = download_button.get_attribute("href")
    assert href and href.endswith("/download")


@pytest.mark.playwright
def test_ui_wizard_llm_mode_happy_path(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("要件プロンプト").fill(
        "force retry Build an invoice validation assistant that retries on the first validation attempt"
    )
    page.get_by_role("switch", name="モックモード").click()
    page.get_by_label("ユーザー ID").fill("ui-llm-user")
    page.get_by_label("プロジェクト ID").fill("ui-llm-project")
    page.get_by_label("プロジェクト名").fill("UI LLM Integration Test")
    page.get_by_label("プロジェクト概要").fill("LLM フローの自動テストから生成されたプロジェクト")

    page.get_by_role("button", name="生成を開始").click()

    dashboard = page.get_by_test_id("llm-dashboard")
    dashboard.wait_for(timeout=15000)

    yaml_block = page.get_by_test_id("llm-yaml-preview").locator("pre")
    yaml_block.wait_for(timeout=20000)

    validation_card = page.get_by_test_id("llm-validation-card")
    validation_card.get_by_text("成功", exact=False).wait_for(timeout=10000)

    analysis_card = page.get_by_test_id("llm-analysis-card")
    analysis_card.get_by_text("カテゴリ:", exact=False).first.wait_for(timeout=10000)

    download_button = page.get_by_role("button", name="ZIP をダウンロード")
    download_button.wait_for(timeout=20000)
    href = download_button.get_attribute("href")
    assert href and href.endswith("/download")


@pytest.mark.playwright
def test_ui_wizard_llm_validation_error(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("要件プロンプト").fill(
        "force failure Build a validation assistant that should fail for testing error handling"
    )
    page.get_by_role("switch", name="モックモード").click()
    page.get_by_label("ユーザー ID").fill("ui-llm-error")
    page.get_by_label("プロジェクト ID").fill("ui-llm-error-project")
    page.get_by_label("プロジェクト名").fill("UI LLM Error Test")
    page.get_by_label("プロジェクト概要").fill("LLM エラーシナリオのテスト")

    page.get_by_role("button", name="生成を開始").click()

    alert = page.get_by_role("alert")
    alert.wait_for(timeout=15000)
    assert "Validation is configured to always fail" in alert.inner_text()
    assert "force failure" in alert.inner_text()

