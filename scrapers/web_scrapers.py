import os
import json
import tempfile
import subprocess
from datetime import datetime

class SyncWebScraper:
    """Synchronous wrapper for async web scraping via a subprocess."""

    def scrape_url(self, url: str) -> dict:
        """Scrape a URL using an async Playwright scraper in a separate process."""
        # Prepare a temp script path
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, f"temp_scraper_{int(datetime.now().timestamp())}.py")

        # Content of the async wrapper script
        script_content = f"""
import asyncio
import json
import sys
import os

# Ensure project root is on path
sys.path.append(r"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}")

from scrapers.web_scraper import WebContentScraper

async def main():
    scraper = WebContentScraper()
    await scraper.initialize()
    result = await scraper.scrape_url("{url}")
    await scraper.cleanup()
    print(json.dumps(result))

if __name__ == "__main__":
    asyncio.run(main())
"""

        # Write the temp script
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(script_content)

        try:
            # Execute the temp script
            result = subprocess.run(
                ["python", temp_file],
                capture_output=True,
                text=True
            )

            if result.returncode == 0 and result.stdout:
                # Parse only the last line (in case of logs)
                raw_lines = result.stdout.strip().splitlines()
                try:
                    data = json.loads(raw_lines[-1])
                    # Attach timestamp
                    data.setdefault('timestamp', datetime.now().strftime("%Y%m%d_%H%M%S"))
                    return data
                except json.JSONDecodeError:
                    pass

            # Fallback on failure
            return self._fallback_fetch(url)

        finally:
            # Always clean up
            try:
                os.remove(temp_file)
            except OSError:
                pass

    def _fallback_fetch(self, url: str) -> dict:
        """Fallback method using requests + BeautifulSoup."""
        try:
            import requests
            from bs4 import BeautifulSoup

            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            content_div = soup.find('div', {'id': 'mw-content-text'})
            text = content_div.get_text(strip=True, separator='\n') if content_div else soup.get_text(strip=True, separator='\n')
        except Exception as e:
            text = f"Error fetching content: {e}"

        return {
            'content': text,
            'url': url,
            'screenshot': None,
            'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S")
        }


# web_scraper.py
import asyncio
from datetime import datetime
import os
from playwright.async_api import async_playwright

class WebContentScraper:

    def __init__(self):
        self.browser = None
        self.playwright = None
        self.screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
    async def initialize(self):
        """Launch the headless browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        
    async def scrape_url(self, url: str) -> dict:
        if not self.browser:
            await self.initialize()
            
        page = await self.browser.new_page()
        try:
        
            await page.goto(url, wait_until='networkidle')
            
            
            content = await page.inner_text('#mw-content-text')
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(self.screenshot_dir, f"{timestamp}.png")
            await page.screenshot(path=screenshot_path)
            
            return {
                'content': content,
                'url': url,
                'screenshot': screenshot_path,
                'timestamp': timestamp
            }
            
        finally:
            await page.close()
    
    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()