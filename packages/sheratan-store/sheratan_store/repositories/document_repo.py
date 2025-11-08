"""Document repository for database operations"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..models.documents import Document, DocumentChunk, SearchLog


class DocumentRepository:
    """Repository for document operations"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> Document:
        """Create a new document"""
        doc = Document(
            content=content,
            metadata_=metadata or {},
            source=source
        )
        self.session.add(doc)
        await self.session.flush()
        return doc
    
    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """Get document by ID"""
        result = await self.session.execute(
            select(Document).where(Document.id == document_id)
        )
        return result.scalar_one_or_none()
    
    async def create_chunk(
        self,
        document_id: UUID,
        chunk_index: int,
        content: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentChunk:
        """Create a document chunk with embedding"""
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
            metadata_=metadata or {}
        )
        self.session.add(chunk)
        await self.session.flush()
        return chunk
    
    async def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity
        
        Args:
            query_embedding: Query vector
            top_k: Number of results
            threshold: Minimum similarity threshold (0-1)
            
        Returns:
            List of results with chunk, document, and score
        """
        # Using cosine distance for similarity
        # Note: Actual implementation depends on pgvector setup
        query = select(
            DocumentChunk,
            DocumentChunk.embedding.cosine_distance(query_embedding).label('distance')
        ).order_by('distance').limit(top_k)
        
        result = await self.session.execute(query)
        
        results = []
        for chunk, distance in result:
            # Convert distance to similarity score (1 - distance)
            similarity = 1 - distance
            
            if threshold is None or similarity >= threshold:
                results.append({
                    'chunk_id': str(chunk.id),
                    'document_id': str(chunk.document_id),
                    'content': chunk.content,
                    'score': float(similarity),
                    'metadata': chunk.metadata_
                })
        
        return results
    
    async def log_search(
        self,
        query: str,
        results_count: int,
        avg_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Log a search query for analytics"""
        log = SearchLog(
            query=query,
            results_count=results_count,
            avg_score=avg_score,
            metadata_=metadata or {}
        )
        self.session.add(log)
        await self.session.flush()
