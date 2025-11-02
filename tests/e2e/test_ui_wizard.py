import pytest
from playwright.sync_api import Page


@pytest.mark.playwright
def test_workflow_chat_success(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("要件プロンプト").fill(
        "経理担当者が請求書をアップロードして検証できるアプリを生成して"
    )
    page.get_by_role("button", name="生成を開始").click()

    page.get_by_text("要件アナリスト").wait_for(timeout=20000)
    page.get_by_text("workflow.yaml の生成とパッケージングが完了しました").wait_for(timeout=20000)

    yaml_preview = page.get_by_label("workflow.yaml プレビュー")
    yaml_preview.get_by_text("info").wait_for(timeout=5000)

    download_button = page.get_by_role("button", name="成果物をダウンロード")
    download_button.wait_for(timeout=20000)
    href = download_button.get_attribute("href")
    assert href and href.endswith("/download")

    # Insights accordion should display details
    page.get_by_text("要件分析結果").wait_for(timeout=5000)


@pytest.mark.playwright
def test_workflow_chat_validation_failure(prepare_environment, page: Page) -> None:  # noqa: PT019
    page.goto("http://127.0.0.1:5173/")

    page.get_by_label("要件プロンプト").fill(
        "force failure バリデーションが必ず失敗するワークフローを生成して"
    )
    page.get_by_role("button", name="生成を開始").click()

    alert = page.get_by_role("alert")
    alert.wait_for(timeout=20000)
    assert "workflow.yaml の検証に失敗しました" in alert.inner_text()
    assert "Validation is configured to always fail" in alert.inner_text()
