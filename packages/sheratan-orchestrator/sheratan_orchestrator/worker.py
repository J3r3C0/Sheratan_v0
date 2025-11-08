"""Worker for processing documents: crawl, chunk, embed"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from typing import List, Dict, Any
from datetime import datetime

from .job_manager import JobManager

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
class DocumentProcessor:
    """Processes documents through crawl, chunk, embed pipeline"""
    
    def __init__(self):
        self.is_running = False
        self._embedding_provider = None
        
    def _get_embedding_provider(self):
        """Lazy load embedding provider"""
        if self._embedding_provider is None:
            try:
                # Import here to avoid hard dependency
                from sheratan_embeddings.providers import get_embedding_provider
                self._embedding_provider = get_embedding_provider()
                logger.info("Embedding provider initialized")
            except ImportError:
                logger.warning("sheratan-embeddings not available, embeddings will be skipped")
                self._embedding_provider = None
        return self._embedding_provider
        
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
            List of text chunks
        """
        logger.info(f"Chunking content (size: {len(content)})")
        
        if not content:
            return []
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
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
        
        provider = self._get_embedding_provider()
        results = []
        
        if provider is None:
            logger.warning("No embedding provider available, returning chunks without embeddings")
            for i, chunk in enumerate(chunks):
                results.append({
                    "chunk": chunk,
                    "embedding": [],
                    "index": i
                })
        else:
            try:
                # Generate embeddings using the provider
                embeddings = provider.embed(chunks)
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    results.append({
                        "chunk": chunk,
                        "embedding": embedding,
                        "index": i
                    })
                logger.info(f"Successfully generated {len(embeddings)} embeddings")
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}")
                # Fallback to empty embeddings
                for i, chunk in enumerate(chunks):
                    results.append({
                        "chunk": chunk,
                        "embedding": [],
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
    logger.info("Starting Sheratan Orchestrator Worker")
    
    # Configuration from environment
    poll_interval = int(os.getenv("JOB_POLL_INTERVAL", "5"))
    max_concurrent = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
    
    # Create and start job manager
    manager = JobManager(
        poll_interval=poll_interval,
        max_concurrent_jobs=max_concurrent
    )
    
    try:
        await manager.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await manager.stop()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
