import httpx
import asyncio
from typing import Optional
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PinchtabClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.pinchtab_url
        self.client = httpx.AsyncClient(timeout=settings.request_timeout)
    
    async def navigate(self, url: str) -> bool:
        """Navigate to a URL."""
        try:
            response = await self.client.post(
                f"{self.base_url}/navigate",
                json={"url": url}
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to navigate: {e}")
            return False
    
    async def get_text(self) -> str:
        """Get the text content of the current page."""
        try:
            response = await self.client.get(f"{self.base_url}/text")
            response.raise_for_status()
            data = response.json()
            return data.get("text", "") or ""
        except httpx.HTTPError as e:
            logger.error(f"Failed to get text: {e}")
            raise
    
    async def get_page_content(self, url: str) -> str:
        """Navigate to URL and get text content."""
        if not await self.navigate(url):
            raise RuntimeError(f"Failed to navigate to: {url}")
        
        await asyncio.sleep(2)
        
        return await self.get_text()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
