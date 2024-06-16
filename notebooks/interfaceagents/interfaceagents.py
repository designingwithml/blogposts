import re
from playwright.sync_api import sync_playwright, Page, expect

def test_has_title(page: Page):
    page.goto("https://playwright.dev/")
    
    # Expect a title "to contain" a substring.
    expect(page).to_have_title(re.compile("Playwright"))

def main():
    # Initialize Playwright and manage lifecycle
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        # Run the test
        print("Running test_has_title")
        test_has_title(page)

        # Print the content of the page
        content = page.content()
        print("Page content is:", content)

        # Close the browser
        browser.close()


if __name__ == "__main__":
    main()