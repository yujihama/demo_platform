## Task B: E2Eテストの強化

### 目的
現在の基本的なテストを、より網羅的で信頼性の高いPlaywrightによるE2Eテストスイートに置き換えることで、アプリケーションの品質保証体制を確立します。

### 手順
1. **`tests/e2e/` ディレクトリの作成・更新**: 以下の内容で、ファイルを作成・配置してください。

#### `tests/e2e/conftest.py`
```python
import os
import pytest
from playwright.sync_api import Page

@pytest.fixture(scope="session")
def base_url():
    return os.environ.get("BASE_URL", "http://localhost:3000")

@pytest.fixture
def page(page: Page, base_url: str):
    page.goto(base_url)
    return page
```

#### `tests/e2e/requirements.txt`
```
pytest
playwright
pytest-playwright
```

#### `tests/e2e/test_smoke.py`
```python
from playwright.sync_api import Page, expect

def test_smoke(page: Page):
    # Check if the main page loads correctly
    expect(page.locator("h1")).to_have_text("Demo Platform")

    # Check if the chat input is visible
    chat_input = page.locator("textarea[placeholder*='your application']")
    expect(chat_input).to_be_visible()

    # Send a message and check for the response
    chat_input.fill("Create a simple invoice processing app")
    page.press("textarea[placeholder*='your application']", "Enter")

    # Wait for the response to appear
    response_locator = page.locator("div.prose")
    expect(response_locator).to_be_visible(timeout=30000) # 30s timeout

    # Check if the download button appears
    download_button = page.locator("button:has-text('Download Package')")
    expect(download_button).to_be_visible()
```

2. **CI/CDパイプラインの確認**: PR #24で作成済みの`.github/workflows/ci.yml`に、これらのE2Eテストを実行するステップが含まれていることを確認してください。
