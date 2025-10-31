from __future__ import annotations

import pytest
from playwright.sync_api import Page


@pytest.mark.playwright
def test_ui_wizard_happy_path(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("ユーザー ID").fill("ui-user")
    page.get_by_label("プロジェクト ID").fill("ui-project")
    page.get_by_label("プロジェクト名").fill("UI Integration Test")
    page.get_by_label("概要").fill("UI フローの自動テストから生成されたプロジェクト")

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

