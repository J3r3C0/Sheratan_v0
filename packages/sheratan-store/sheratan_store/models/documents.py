"""Database models"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from datetime import datetime

from ..database import Base


class Document(Base):
    """Document model"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, default={})
    source = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_documents_created', 'created_at'),
        Index('idx_documents_source', 'source'),
    )


class DocumentChunk(Base):
    """Document chunk with vector embedding"""
    __tablename__ = "document_chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))  # Dimension depends on embedding model
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_chunks_document', 'document_id'),
        Index('idx_chunks_embedding', 'embedding', postgresql_using='ivfflat'),
    )


class SearchLog(Base):
    """Search query log for analytics"""
    __tablename__ = "search_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    avg_score = Column(Float)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_search_logs_created', 'created_at'),
    )
