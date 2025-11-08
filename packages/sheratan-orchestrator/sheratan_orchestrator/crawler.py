"""Crawler module for fetching content from URLs"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class Crawler:
    """Web crawler for fetching content from URLs"""
    
    def __init__(self, timeout: int = 30, max_size: int = 10 * 1024 * 1024):
        """
        Initialize crawler
        
        Args:
            timeout: Request timeout in seconds
            max_size: Maximum content size in bytes (default 10MB)
        """
        self.timeout = timeout
        self.max_size = max_size
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def crawl(self, url: str) -> Dict[str, Any]:
        """
        Crawl content from URL
        
        Args:
            url: URL to crawl
            
        Returns:
            Dict with crawled content and metadata
            
        Raises:
            ValueError: If URL is invalid
            aiohttp.ClientError: If request fails
        """
        logger.info(f"Crawling URL: {url}")
        
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")
        
        await self._ensure_session()
        
        start_time = datetime.utcnow()
        
        try:
            async with self.session.get(url) as response:
                # Check status
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                
                # Read content with size limit
                content = await response.text()
                
                if len(content) > self.max_size:
                    logger.warning(f"Content size ({len(content)}) exceeds max size ({self.max_size})")
                    content = content[:self.max_size]
                
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()
                
                result = {
                    "url": url,
                    "content": content,
                    "content_type": content_type,
                    "status_code": response.status,
                    "size": len(content),
                    "duration": duration,
                    "timestamp": end_time.isoformat(),
                    "success": True,
                    "metadata": {
                        "headers": dict(response.headers),
                        "final_url": str(response.url),
                    }
                }
                
                logger.info(f"Successfully crawled {url}: {len(content)} bytes in {duration:.2f}s")
                return result
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to crawl {url}: {e}")
            return {
                "url": url,
                "content": "",
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Unexpected error crawling {url}: {e}")
            return {
                "url": url,
                "content": "",
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def crawl_multiple(self, urls: list[str]) -> list[Dict[str, Any]]:
        """
        Crawl multiple URLs concurrently
        
        Args:
            urls: List of URLs to crawl
            
        Returns:
            List of crawl results
        """
        logger.info(f"Crawling {len(urls)} URLs")
        
        await self._ensure_session()
        
        tasks = [self.crawl(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "url": urls[i],
                    "content": "",
                    "error": str(result),
                    "success": False,
                    "timestamp": datetime.utcnow().isoformat()
                })
            else:
                processed_results.append(result)
        
        return processed_results
