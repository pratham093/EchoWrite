"""
Async Web Content Scraper using Playwright.
Handles headless browser automation for content extraction and screenshots.
"""

import os
from datetime import datetime
from playwright.async_api import async_playwright

from config.settings import settings


class WebContentScraper:
    """Async scraper with Playwright for full browser rendering + screenshots."""

    def __init__(self):
        self.browser = None
        self.playwright = None
        self.screenshot_dir = settings.SCREENSHOT_DIR
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Launch the headless Chromium browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

    async def scrape_url(self, url: str) -> dict:
        """
        Navigate to a URL, extract text content, and capture a screenshot.
        Returns dict with content, url, screenshot path, and timestamp.
        """
        if not self.browser:
            await self.initialize()

        page = await self.browser.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=settings.SCRAPE_TIMEOUT * 1000)

            # Try multiple content selectors in priority order
            content = ""
            selectors = [
                "#mw-content-text",   # Wikipedia / Wikisource
                "article",
                "main",
                ".content",
                "#content",
                "body",
            ]
            for sel in selectors:
                try:
                    element = await page.query_selector(sel)
                    if element:
                        content = await element.inner_text()
                        if content.strip():
                            break
                except Exception:
                    continue

            if not content.strip():
                content = await page.inner_text("body")

            # Clean up content
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            content = "\n".join(lines)

            # Capture screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = str(self.screenshot_dir / f"{timestamp}_playwright.png")
            await page.screenshot(path=screenshot_path, full_page=True)

            title = await page.title()

            return {
                "content": content,
                "title": title or "No title",
                "url": url,
                "success": True,
                "screenshot": screenshot_path,
                "timestamp": timestamp,
            }

        except Exception as e:
            return {
                "content": "",
                "title": "",
                "url": url,
                "success": False,
                "error": str(e),
                "screenshot": None,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
            }
        finally:
            await page.close()

    async def cleanup(self):
        """Close browser and Playwright."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
