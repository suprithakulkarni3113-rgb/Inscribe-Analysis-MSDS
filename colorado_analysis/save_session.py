"""Run this ONCE to save your InScribe login session."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://inscribe.education/main/colorado/6754110229507555/channels")
    input("\nLog in to InScribe in the browser, wait for channels to load, then press ENTER: ")
    context.storage_state(path=r"C:\Users\Supritha Kulkarni\colorado_analysis\session.json")
    print("Session saved to session.json")
    browser.close()
