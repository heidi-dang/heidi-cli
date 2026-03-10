from playwright.sync_api import sync_playwright
import sys


def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    try:
        page.goto("http://localhost:3000")

        # Wait for something distinctive to load
        page.wait_for_selector("textarea[aria-label='Prompt input']", timeout=10000)

        # Click on "Loop" mode button to reveal the Retries input
        print("Clicking Loop mode button...")
        page.get_by_role("button", name="Loop").click()

        # Wait for the retries input to appear (it has animation)
        page.wait_for_timeout(1000)

        # Verify Retries label works
        # If I used <label> correctly, get_by_label("Retries") should find the input.
        print("Looking for Retries input by label...")
        retries_input = page.get_by_label("Retries")

        if retries_input.is_visible():
            print("SUCCESS: Retries input found by label!")
            # Take a screenshot
            page.screenshot(path="verification_retries.png")
        else:
            print("FAILURE: Retries input NOT visible or not found by label.")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        browser.close()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)
