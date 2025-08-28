# hello_playwright.py
from playwright.sync_api import sync_playwright
from icici_nysa import run_icici_nysa

def main():
    # with sync_playwright() as p:
    #     browser = p.chromium.launch()       # headless by default on CI
    #     page = browser.new_page()
    #     page.goto("https://example.com")
    #     print("Title:", page.title())
    #     browser.close()
    run_icici_nysa()

if __name__ == "__main__":
    main()
