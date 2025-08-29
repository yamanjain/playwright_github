# hello_playwright.py
from playwright.sync_api import sync_playwright
from icici_nysa import run_icici_nysa
from hirise_get_vahan_csv import hirise_vahan

# Try loading .env if it exists (only affects local dev)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed (CI/CD case), ignore

def main():
    # with sync_playwright() as p:
    #     browser = p.chromium.launch()       # headless by default on CI
    #     page = browser.new_page()
    #     page.goto("https://example.com")
    #     print("Title:", page.title())
    #     browser.close()
    hirise_vahan()
    run_icici_nysa()

if __name__ == "__main__":
    main()
