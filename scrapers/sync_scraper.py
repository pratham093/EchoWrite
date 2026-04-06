"""
Synchronous Web Scraper with multi-method screenshot capture.
Provides fallback chain: Playwright → Selenium → Pyppeteer → HTML save.
"""

import os
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from config.settings import settings


class SyncWebScraper:
    """Sync scraper using requests + BeautifulSoup, with screenshot fallbacks."""

    def __init__(self):
        self.screenshot_dir = settings.SCREENSHOT_DIR
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def scrape_url(self, url: str) -> dict:
        """Fetch URL, extract cleaned text, and attempt a screenshot."""
        try:
            headers = {"User-Agent": settings.USER_AGENT}
            response = requests.get(url, headers=headers, timeout=settings.SCRAPE_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Try content selectors in priority order
            content = ""
            selectors = [
                ("#mw-content-text", "id"),
                ("article", "tag"),
                ("main", "tag"),
                (".content", "class"),
                ("#content", "id"),
            ]

            for selector, sel_type in selectors:
                element = None
                if sel_type == "id":
                    element = soup.find(id=selector.lstrip("#"))
                elif sel_type == "class":
                    element = soup.find(class_=selector.lstrip("."))
                elif sel_type == "tag":
                    element = soup.find(selector)

                if element:
                    # Strip noise tags
                    for tag in element(["script", "style", "nav", "aside", "footer", "header"]):
                        tag.decompose()
                    content = element.get_text(strip=True, separator="\n")
                    break

            if not content:
                content = soup.get_text(strip=True, separator="\n")

            # Clean whitespace
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            content = "\n".join(lines)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self._capture_screenshot(url, timestamp)

            return {
                "content": content,
                "title": soup.title.string if soup.title else "No title",
                "url": url,
                "success": True,
                "timestamp": timestamp,
                "screenshot": screenshot_path,
            }

        except Exception as e:
            return {
                "content": "",
                "error": str(e),
                "url": url,
                "success": False,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
                "screenshot": None,
            }

    # ------------------------------------------------------------------
    # Screenshot fallback chain
    # ------------------------------------------------------------------
    def _capture_screenshot(self, url: str, timestamp: str) -> str | None:
        """Try multiple screenshot backends; return path or None."""
        methods = [
            self._screenshot_playwright,
            self._screenshot_selenium,
            self._screenshot_pyppeteer,
            self._save_html_fallback,
        ]
        for method in methods:
            try:
                path = method(url, timestamp)
                if path and Path(path).exists():
                    print(f"✅ Screenshot saved: {path}")
                    return path
            except Exception as e:
                print(f"⚠️  Screenshot method {method.__name__} failed: {e}")
        print("⚠️  All screenshot methods failed")
        return None

    def _screenshot_playwright(self, url: str, ts: str) -> str:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            path = str(self.screenshot_dir / f"{ts}_playwright.png")
            page.screenshot(path=path, full_page=True)
            browser.close()
        return path

    def _screenshot_selenium(self, url: str, ts: str) -> str:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        opts = Options()
        for flag in [
            "--headless",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1920,1080",
        ]:
            opts.add_argument(flag)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=opts)
        driver.get(url)
        driver.implicitly_wait(5)
        path = str(self.screenshot_dir / f"{ts}_selenium.png")
        driver.save_screenshot(path)
        driver.quit()
        return path

    def _screenshot_pyppeteer(self, url: str, ts: str) -> str:
        import asyncio
        from pyppeteer import launch

        async def _capture():
            browser = await launch(headless=True, args=["--no-sandbox"])
            page = await browser.newPage()
            await page.goto(url, {"waitUntil": "networkidle2"})
            p = str(self.screenshot_dir / f"{ts}_pyppeteer.png")
            await page.screenshot({"path": p, "fullPage": True})
            await browser.close()
            return p

        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(_capture())
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    def _save_html_fallback(self, url: str, ts: str) -> str:
        """Last resort — save rendered HTML to disk."""
        resp = requests.get(url, timeout=10)
        html_path = str(self.screenshot_dir / f"{ts}_content.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(
                f"<html><head><title>Captured: {url}</title></head>"
                f"<body><p><b>URL:</b> {url}<br><b>Time:</b> {ts}</p>"
                f"<hr>{resp.text}</body></html>"
            )
        return html_path
