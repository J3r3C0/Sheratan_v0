"""ETL Pipeline processor integrating crawl, parse, chunk, embed, and upsert"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from .crawler import Crawler
from .parser import ContentParser
from .chunker import TextChunker

logger = logging.getLogger(__name__)


class ETLPipeline:
    """Complete ETL pipeline for document processing"""
    
    def __init__(
        self,
        embedding_provider=None,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ):
        """
        Initialize ETL pipeline
        
        Args:
            embedding_provider: Embedding provider instance (from sheratan-embeddings)
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks
        """
        self.crawler = Crawler()
        self.parser = ContentParser()
        self.chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.embedding_provider = embedding_provider
    
    async def close(self):
        """Clean up resources"""
        await self.crawler.close()
    
    async def process_url(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a URL through the complete ETL pipeline
        
        Args:
            url: URL to process
            metadata: Optional metadata to attach
            
        Returns:
            Processing result with chunks and embeddings
        """
        logger.info(f"Starting ETL pipeline for URL: {url}")
        
        result = {
            "url": url,
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        try:
            # Step 1: Crawl
            logger.info("Step 1: Crawling...")
            crawl_result = await self.crawler.crawl(url)
            
            if not crawl_result.get("success"):
                result["error"] = f"Crawl failed: {crawl_result.get('error', 'Unknown error')}"
                result["step"] = "crawl"
                return result
            
            result["crawl"] = {
                "size": crawl_result.get("size"),
                "content_type": crawl_result.get("content_type"),
                "duration": crawl_result.get("duration")
            }
            
            # Step 2: Parse
            logger.info("Step 2: Parsing...")
            content = crawl_result.get("content", "")
            content_type = crawl_result.get("content_type", "text/plain")
            
            parse_result = self.parser.parse(content, content_type)
            
            if not parse_result.get("success"):
                result["error"] = f"Parse failed: {parse_result.get('error', 'Unknown error')}"
                result["step"] = "parse"
                return result
            
            text = parse_result.get("text", "")
            result["parse"] = {
                "format": parse_result.get("format"),
                "text_length": len(text)
            }
            
            # Step 3: Chunk
            logger.info("Step 3: Chunking...")
            chunks = self.chunker.chunk(text, metadata={
                "url": url,
                "content_type": content_type,
                **(metadata or {})
            })
            
            result["chunk"] = {
                "count": len(chunks),
                "avg_length": sum(c["length"] for c in chunks) / len(chunks) if chunks else 0
            }
            
            # Step 4: Embed
            if self.embedding_provider and chunks:
                logger.info("Step 4: Embedding...")
                embeddings = await self._embed_chunks(chunks)
                result["embed"] = {
                    "count": len(embeddings),
                    "dimension": len(embeddings[0]) if embeddings else 0
                }
            else:
                logger.info("Step 4: Skipping embedding (no provider)")
                embeddings = []
                result["embed"] = {"count": 0}
            
            # Combine chunks with embeddings
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_data = {
                    "text": chunk["text"],
                    "index": chunk["index"],
                    "metadata": chunk["metadata"],
                    "embedding": embeddings[i] if i < len(embeddings) else None
                }
                processed_chunks.append(chunk_data)
            
            result["chunks"] = processed_chunks
            result["success"] = True
            result["step"] = "completed"
            
            logger.info(f"ETL pipeline completed successfully: {len(processed_chunks)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"ETL pipeline error: {e}")
            result["error"] = str(e)
            result["step"] = result.get("step", "unknown")
            return result
    
    async def process_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process raw text through chunk and embed pipeline
        
        Args:
            text: Text to process
            metadata: Optional metadata
            
        Returns:
            Processing result
        """
        logger.info(f"Processing text of length {len(text)}")
        
        result = {
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        try:
            # Step 1: Chunk
            logger.info("Step 1: Chunking...")
            chunks = self.chunker.chunk(text, metadata=metadata)
            
            result["chunk"] = {
                "count": len(chunks),
                "avg_length": sum(c["length"] for c in chunks) / len(chunks) if chunks else 0
            }
            
            # Step 2: Embed
            if self.embedding_provider and chunks:
                logger.info("Step 2: Embedding...")
                embeddings = await self._embed_chunks(chunks)
                result["embed"] = {
                    "count": len(embeddings),
                    "dimension": len(embeddings[0]) if embeddings else 0
                }
            else:
                embeddings = []
                result["embed"] = {"count": 0}
            
            # Combine
            processed_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_data = {
                    "text": chunk["text"],
                    "index": chunk["index"],
                    "metadata": chunk["metadata"],
                    "embedding": embeddings[i] if i < len(embeddings) else None
                }
                processed_chunks.append(chunk_data)
            
            result["chunks"] = processed_chunks
            result["success"] = True
            
            logger.info(f"Text processing completed: {len(processed_chunks)} chunks")
            return result
            
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            result["error"] = str(e)
            return result
    
    async def _embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """
        Generate embeddings for chunks
        
        Args:
            chunks: List of chunk dictionaries
            
        Returns:
            List of embedding vectors
        """
        if not self.embedding_provider:
            return []
        
        texts = [chunk["text"] for chunk in chunks]
        
        try:
            # Check if provider has async method
            if hasattr(self.embedding_provider, 'embed_async'):
                embeddings = await self.embedding_provider.embed_async(texts)
            else:
                # Fallback to sync method (run in executor if needed)
                import asyncio
                loop = asyncio.get_event_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    self.embedding_provider.embed,
                    texts
                )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    async def upsert_to_store(
        self,
        chunks: List[Dict[str, Any]],
        document_id: Optional[uuid.UUID],
        db_session
    ) -> Dict[str, Any]:
        """
        Upsert processed chunks to database
        
        Args:
            chunks: Processed chunks with embeddings
            document_id: Document ID (creates new if None)
            db_session: Database session
            
        Returns:
            Upsert result
        """
        from sheratan_store.models import Document, DocumentChunk
        from sheratan_store.repositories import DocumentRepository
        
        logger.info(f"Upserting {len(chunks)} chunks to database")
        
        try:
            repo = DocumentRepository(db_session)
            
            # Create or get document
            if document_id:
                document = await repo.get_document(document_id)
                if not document:
                    raise ValueError(f"Document {document_id} not found")
            else:
                # Create new document from first chunk metadata
                metadata = chunks[0].get("metadata", {}) if chunks else {}
                document = Document(
                    id=uuid.uuid4(),
                    content=" ".join(c["text"] for c in chunks[:5]),  # Preview
                    metadata=metadata,
                    source=metadata.get("url", "unknown")
                )
                db_session.add(document)
                await db_session.flush()
            
            # Insert chunks
            inserted_chunks = []
            for chunk_data in chunks:
                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    chunk_index=chunk_data["index"],
                    content=chunk_data["text"],
                    embedding=chunk_data.get("embedding"),
                    metadata=chunk_data.get("metadata", {})
                )
                db_session.add(chunk)
                inserted_chunks.append(chunk)
            
            await db_session.flush()
            
            logger.info(f"Successfully upserted {len(inserted_chunks)} chunks for document {document.id}")
            
            return {
                "success": True,
                "document_id": str(document.id),
                "chunks_inserted": len(inserted_chunks)
            }
            
        except Exception as e:
            logger.error(f"Upsert error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
