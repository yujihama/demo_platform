from playwright.sync_api import Page, expect

def test_smoke(page_with_base_url: Page):
    """Smoke test to verify basic functionality of the application."""
    # Check if the main page loads correctly
    expect(page_with_base_url.locator("h1")).to_have_text("Demo Platform")

    # Check if the chat input is visible
    chat_input = page_with_base_url.locator("textarea[placeholder*='your application']")
    expect(chat_input).to_be_visible()

    # Send a message and check for the response
    chat_input.fill("Create a simple invoice processing app")
    page_with_base_url.press("textarea[placeholder*='your application']", "Enter")

    # Wait for the response to appear
    response_locator = page_with_base_url.locator("div.prose")
    expect(response_locator).to_be_visible(timeout=30000) # 30s timeout

    # Check if the download button appears
    download_button = page_with_base_url.locator("button:has-text('Download Package')")
    expect(download_button).to_be_visible()
