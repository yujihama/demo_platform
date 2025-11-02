from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.playwright
@pytest.mark.usefixtures("prepare_environment")
def test_conversation_ui_generates_workflow(page: Page, tmp_path: Path) -> None:
    page.goto("http://127.0.0.1:5173/")

    page.get_by_role("heading", name="宣言的アプリ生成デモ").wait_for(timeout=5000)

    prompt_input = page.get_by_label("例: 請求書からデータを抽出するアプリを作って")
    prompt_input.click()
    prompt_input.fill("請求書からデータを抽出するアプリを作って")

    page.get_by_role("button", name="会話を開始").click()

    page.get_by_text("workflow.yamlの生成が完了しました").wait_for(timeout=25000)

    preview = page.locator("pre").first
    preview.wait_for(timeout=5000)
    preview_text = preview.inner_text()
    assert "pipeline:" in preview_text

    download_button = page.get_by_role("button", name="パッケージをダウンロード")
    expect(download_button).to_be_enabled(timeout=20000)

    with page.expect_download(timeout=20000) as download_info:
        download_button.click()
    download = download_info.value

    zip_path = tmp_path / "app.zip"
    download.save_as(str(zip_path))

    assert zip_path.exists()
    with zipfile.ZipFile(zip_path) as archive:
        members = set(archive.namelist())

    expected_files = {"workflow.yaml", "docker-compose.yml", ".env.example", "README.md"}
    assert expected_files.issubset(members)


@pytest.mark.playwright
@pytest.mark.usefixtures("prepare_environment")
def test_conversation_ui_handles_failure(page: Page) -> None:
    page.goto("http://127.0.0.1:5173/")

    page.get_by_role("heading", name="宣言的アプリ生成デモ").wait_for(timeout=5000)

    prompt_input = page.get_by_label("例: 請求書からデータを抽出するアプリを作って")
    prompt_input.click()
    prompt_input.fill("force failure Build a validation assistant that should fail for testing error handling")

    page.get_by_role("button", name="会話を開始").click()

    page.get_by_text("生成に失敗しました").wait_for(timeout=25000)
    page.get_by_text("force failure").wait_for(timeout=25000)

    status_chip = page.get_by_text("失敗")
    status_chip.wait_for(timeout=5000)

    download_button = page.get_by_role("button", name="パッケージをダウンロード")
    expect(download_button).to_be_disabled()

    preview_alert = page.get_by_text("workflow.yaml が生成されるとプレビューが表示されます。")
    preview_alert.wait_for(timeout=5000)
