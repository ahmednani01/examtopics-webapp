from playwright.async_api import async_playwright, Browser, Page
import asyncio
from typing import Optional
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PlaywrightClient:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
    
    async def _ensure_browser(self) -> None:
        """Ensure browser is launched."""
        if self.browser is None:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.page = await self.browser.new_page()
    
    async def navigate(self, url: str) -> bool:
        """Navigate to a URL."""
        try:
            await self._ensure_browser()
            await self.page.goto(url, wait_until='domcontentloaded', timeout=settings.request_timeout * 1000)
            await asyncio.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False
    
    async def get_text(self) -> str:
        """Get the text content of the current page."""
        try:
            if self.page is None:
                raise RuntimeError("No page loaded. Call navigate first.")
            return await self.page.evaluate("""() => {
                return document.body.innerText;
            }""")
        except Exception as e:
            logger.error(f"Failed to get text: {e}")
            raise
    
    async def get_page_content(self, url: str) -> str:
        """Navigate to URL and get text content."""
        if not await self.navigate(url):
            raise RuntimeError(f"Failed to navigate to: {url}")
        
        return await self.get_text()
    
    async def close(self) -> None:
        """Close the browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.browser = None
        self.playwright = None
        self.page = None
