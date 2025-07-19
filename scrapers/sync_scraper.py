import os
import sys
import json
import tempfile
import subprocess
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from pathlib import Path

class SyncWebScraper:
    def __init__(self):
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)

    def scrape_url(self, url: str) -> dict:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content = ""
            for selector in ['#mw-content-text', 'article', 'main', '.content', '#content']:
                element = soup.find(id=selector[1:] if selector.startswith('#') else None,
                                  class_=selector[1:] if selector.startswith('.') else None,
                                  name=selector if not selector.startswith(('#', '.')) else None)
                if element:
                    for tag in element(['script', 'style', 'nav', 'aside']):
                        tag.decompose()
                    content = element.get_text(strip=True, separator='\n')
                    break
            
            if not content:
                content = soup.get_text(strip=True, separator='\n')
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            content = '\n'.join(lines)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            screenshot_path = self.capture_screenshot_simple(url, timestamp)
            
            return {
                'content': content,
                'title': soup.title.string if soup.title else 'No title',
                'url': url,
                'success': True,
                'timestamp': timestamp,
                'screenshot': screenshot_path
            }
            
        except Exception as e:
            return {
                'content': '',
                'error': str(e),
                'url': url,
                'success': False,
                'timestamp': datetime.now().strftime("%Y%m%d_%H%M%S"),
                'screenshot': None
            }
    
    def capture_screenshot_simple(self, url: str, timestamp: str) -> str:
        """Simple screenshot capture using multiple methods"""
        
        methods = [
            self._screenshot_playwright,
            self._screenshot_selenium,
            self._screenshot_pyppeteer,
            self._screenshot_requests_html
        ]
        
        for method in methods:
            try:
                screenshot_path = method(url, timestamp)
                if screenshot_path and Path(screenshot_path).exists():
                    print(f"✅ Screenshot saved: {screenshot_path}")
                    return screenshot_path
            except Exception as e:
                print(f"Screenshot method failed: {e}")
                continue
        
        print("⚠️ All screenshot methods failed - saving HTML instead")
        return self._save_html_as_screenshot(url, timestamp)
    
    def _screenshot_playwright(self, url: str, timestamp: str) -> str:
        """Method 1: Using Playwright"""
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle")
            
            screenshot_path = self.screenshot_dir / f"{timestamp}_playwright.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            
            browser.close()
            return str(screenshot_path)
    
    def _screenshot_selenium(self, url: str, timestamp: str) -> str:
        """Method 2: Using Selenium"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.get(url)
        driver.implicitly_wait(5)
        
        screenshot_path = self.screenshot_dir / f"{timestamp}_selenium.png"
        driver.save_screenshot(str(screenshot_path))
        driver.quit()
        
        return str(screenshot_path)
    
    def _screenshot_pyppeteer(self, url: str, timestamp: str) -> str:
        """Method 3: Using Pyppeteer"""
        import asyncio
        from pyppeteer import launch
        
        async def capture():
            browser = await launch(headless=True, args=['--no-sandbox'])
            page = await browser.newPage()
            await page.goto(url, {'waitUntil': 'networkidle2'})
            
            screenshot_path = self.screenshot_dir / f"{timestamp}_pyppeteer.png"
            await page.screenshot({'path': str(screenshot_path), 'fullPage': True})
            
            await browser.close()
            return str(screenshot_path)
        
        return asyncio.get_event_loop().run_until_complete(capture())
    
    def _screenshot_requests_html(self, url: str, timestamp: str) -> str:
        """Method 4: Using requests-html"""
        from requests_html import HTMLSession
        
        session = HTMLSession()
        r = session.get(url)
        r.html.render(timeout=20)
        
        screenshot_path = self.screenshot_dir / f"{timestamp}_requests_html.png"
        r.html.screenshot(str(screenshot_path))
        
        return str(screenshot_path)
    
    def _save_html_as_screenshot(self, url: str, timestamp: str) -> str:
        """Fallback: Save HTML content when screenshot fails"""
        try:
            response = requests.get(url, timeout=10)
            html_path = self.screenshot_dir / f"{timestamp}_content.html"
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(f"""
                <html>
                <head>
                    <title>Captured: {url}</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; padding: 20px; }}
                        .meta {{ background: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="meta">
                        <h2>Page Capture</h2>
                        <p><strong>URL:</strong> {url}</p>
                        <p><strong>Captured:</strong> {timestamp}</p>
                    </div>
                    <div class="content">
                        {response.text}
                    </div>
                </body>
                </html>
                """)
            
            print(f"📄 HTML saved: {html_path}")
            return str(html_path)
        except:
            return None