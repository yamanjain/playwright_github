from playwright.sync_api import Playwright
import sys


def get_playwright_page(p: Playwright, matchers, slow_mo=0):
    do_headless = True
    if (sys.platform == "win32"):
        do_headless = False
    browser = p.chromium.launch(headless=do_headless, chromium_sandbox=False)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    page.evaluate("document.body.style.zoom=1.0")
    return [browser, page, context, False]
