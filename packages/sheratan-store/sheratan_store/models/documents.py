"""Database models"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, JSON, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
import os
from datetime import datetime

from ..database import Base

# Get vector dimension from environment or use default
VECTOR_DIMENSION = int(os.getenv("VECTOR_DIMENSION", "384"))


class Document(Base):
    """Document model"""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    metadata_ = Column('metadata', JSON, default={})  # Use metadata_ to avoid conflict with Base.metadata
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
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(VECTOR_DIMENSION))  # Configurable dimension
    metadata_ = Column('metadata', JSON, default={})  # Use metadata_ to avoid conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_chunks_document', 'document_id'),
        Index('idx_chunks_embedding', 'embedding', postgresql_using='ivfflat', postgresql_ops={'embedding': 'vector_cosine_ops'}),
    )


class AuditLog(Base):
    """Audit log for security and compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False)  # e.g., 'document_access', 'search', 'api_call'
    user_id = Column(String(255))  # User identifier
    action = Column(String(100), nullable=False)  # e.g., 'create', 'read', 'update', 'delete'
    resource_type = Column(String(50))  # e.g., 'document', 'chunk', 'job'
    resource_id = Column(String(255))  # ID of affected resource
    details = Column(JSON, default={})  # Additional event details
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_event_type', 'event_type'),
        Index('idx_audit_user', 'user_id'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )


class SearchLog(Base):
    """Search query log for analytics"""
    __tablename__ = "search_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query = Column(Text, nullable=False)
    results_count = Column(Integer, default=0)
    avg_score = Column(Float)
    metadata_ = Column('metadata', JSON, default={})  # Use metadata_ to avoid conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_search_logs_created', 'created_at'),
    )
