"""Worker for processing documents: crawl, chunk, embed"""
import asyncio
import logging
import os
import sys
from typing import List, Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Guard
GUARD_ENABLED = os.getenv("GUARD_ENABLED", "true").lower() == "true"
guard_middleware = None

if GUARD_ENABLED:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../sheratan-guard"))
        from sheratan_guard import GuardMiddleware, AuditEventType
        
        guard_middleware = GuardMiddleware(enabled=True)
        logger.info("Guard middleware enabled in orchestrator")
    except Exception as e:
        logger.warning(f"Failed to initialize guard middleware in orchestrator: {e}")
        GUARD_ENABLED = False


class DocumentProcessor:
    """Processes documents through crawl, chunk, embed pipeline"""
    
    def __init__(self):
        self.is_running = False
        
    async def crawl(self, url: str) -> Dict[str, Any]:
        """
        Crawl content from URL
        
        Args:
            url: URL to crawl
            
        Returns:
            Dict with crawled content and metadata
        """
        logger.info(f"Crawling: {url}")
        # TODO: Implement actual crawling logic
        return {
            "url": url,
            "content": "",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending"
        }
    
    async def chunk(self, content: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        Split content into chunks
        
        Args:
            content: Text content to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks (with PII scrubbed if guard is enabled)
        """
        logger.info(f"Chunking content (size: {len(content)})")
        
        if not content:
            return []
        
        # Scrub PII from content before chunking
        scrubbed_content = content
        if guard_middleware:
            scrubbed_content = guard_middleware.scrub_pii(content)
            if scrubbed_content != content:
                logger.info("PII detected and scrubbed from content before chunking")
        
        chunks = []
        start = 0
        
        while start < len(scrubbed_content):
            end = start + chunk_size
            chunk = scrubbed_content[start:end]
            chunks.append(chunk)
            start = end - overlap
            
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    async def embed(self, chunks: List[str]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for chunks
        
        Args:
            chunks: List of text chunks
            
        Returns:
            List of dicts with chunk and embedding
        """
        logger.info(f"Generating embeddings for {len(chunks)} chunks")
        # TODO: Use sheratan-embeddings to generate actual embeddings
        
        results = []
        for i, chunk in enumerate(chunks):
            results.append({
                "chunk": chunk,
                "embedding": [],  # Placeholder
                "index": i
            })
        
        return results
    
    async def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single document through the pipeline
        
        Args:
            document: Document dict with 'content' or 'url'
            
        Returns:
            Processing result
        """
        logger.info(f"Processing document: {document.get('id', 'unknown')}")
        
        try:
            # Get content
            if 'url' in document:
                crawl_result = await self.crawl(document['url'])
                content = crawl_result['content']
            else:
                content = document.get('content', '')
            
            # Chunk
            chunks = await self.chunk(content)
            
            # Embed
            embeddings = await self.embed(chunks)
            
            # TODO: Store in sheratan-store
            
            return {
                "success": True,
                "document_id": document.get('id'),
                "chunks_created": len(chunks),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {
                "success": False,
                "document_id": document.get('id'),
                "error": str(e)
            }
    
    async def run(self):
        """Main worker loop"""
        logger.info("Starting orchestrator worker...")
        self.is_running = True
        
        while self.is_running:
            try:
                # TODO: Poll queue for new documents to process
                # For now, just sleep
                await asyncio.sleep(5)
                logger.debug("Waiting for documents...")
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop the worker"""
        logger.info("Stopping orchestrator worker...")
        self.is_running = False


async def main():
    """Entry point for worker"""
    processor = DocumentProcessor()
    try:
        await processor.run()
    except KeyboardInterrupt:
        processor.stop()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
