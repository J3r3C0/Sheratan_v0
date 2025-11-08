"""API client for Sheratan Gateway"""
import os
import httpx
from typing import List, Dict, Any, Optional
import asyncio


class GatewayClient:
    """Client for interacting with Sheratan Gateway API"""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize gateway client
        
        Args:
            base_url: Gateway base URL (defaults to env GATEWAY_URL)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv(
            "GATEWAY_URL",
            f"http://{os.getenv('GATEWAY_HOST', 'localhost')}:{os.getenv('GATEWAY_PORT', '8000')}"
        )
        self.timeout = timeout
    
    async def health_check(self) -> Dict[str, Any]:
        """Check gateway health"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
    
    async def ingest_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Ingest documents via gateway
        
        Args:
            documents: List of documents with 'content', 'metadata', 'source'
            
        Returns:
            Response with document IDs
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/ingest",
                json={"documents": documents}
            )
            response.raise_for_status()
            return response.json()
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Search documents
        
        Args:
            query: Search query
            top_k: Number of results
            filters: Optional filters
            
        Returns:
            Search results
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/search",
                json={
                    "query": query,
                    "top_k": top_k,
                    "filters": filters
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def answer(
        self,
        question: str,
        top_k: int = 5,
        context_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get RAG-based answer
        
        Args:
            question: Question to answer
            top_k: Number of context documents
            context_filters: Optional filters
            
        Returns:
            Answer with sources
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/answer",
                json={
                    "question": question,
                    "top_k": top_k,
                    "context_filters": context_filters
                }
            )
            response.raise_for_status()
            return response.json()


def run_async(coro):
    """Helper to run async functions in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)
