"""Pydantic schemas for validation and serialization"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class DocumentBase(BaseModel):
    """Base document schema"""
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Document metadata")
    source: Optional[str] = Field(None, max_length=500, description="Document source URL or path")


class DocumentCreate(DocumentBase):
    """Schema for creating a document"""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating a document"""
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    source: Optional[str] = Field(None, max_length=500)


class DocumentResponse(DocumentBase):
    """Schema for document response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class ChunkBase(BaseModel):
    """Base chunk schema"""
    document_id: UUID
    chunk_index: int = Field(..., ge=0, description="Index of chunk in document")
    content: str = Field(..., min_length=1, description="Chunk content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk metadata")


class ChunkCreate(ChunkBase):
    """Schema for creating a chunk"""
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")


class ChunkResponse(ChunkBase):
    """Schema for chunk response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime


class VectorSearchRequest(BaseModel):
    """Schema for vector search request"""
    query: str = Field(..., min_length=1, description="Search query")
    top_k: int = Field(5, ge=1, le=100, description="Number of results to return")
    threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Minimum similarity threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")


class VectorSearchResult(BaseModel):
    """Schema for vector search result"""
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobBase(BaseModel):
    """Base job schema"""
    job_type: str = Field(..., max_length=50, description="Type of job")
    status: str = Field(..., max_length=20, description="Job status")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Job payload")
    priority: int = Field(0, description="Job priority (higher = more priority)")


class JobCreate(JobBase):
    """Schema for creating a job"""
    pass


class JobUpdate(BaseModel):
    """Schema for updating a job"""
    status: Optional[str] = Field(None, max_length=20)
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class JobResponse(JobBase):
    """Schema for job response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AuditLogBase(BaseModel):
    """Base audit log schema"""
    event_type: str = Field(..., max_length=50, description="Type of event")
    user_id: Optional[str] = Field(None, max_length=255, description="User ID")
    action: str = Field(..., max_length=100, description="Action performed")
    resource_type: Optional[str] = Field(None, max_length=50, description="Resource type")
    resource_id: Optional[str] = Field(None, max_length=255, description="Resource ID")
    details: Dict[str, Any] = Field(default_factory=dict, description="Event details")
    ip_address: Optional[str] = Field(None, max_length=45, description="IP address")
    user_agent: Optional[str] = Field(None, max_length=500, description="User agent")


class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log"""
    pass


class AuditLogResponse(AuditLogBase):
    """Schema for audit log response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime


class SearchLogCreate(BaseModel):
    """Schema for creating a search log"""
    query: str = Field(..., min_length=1)
    results_count: int = Field(0, ge=0)
    avg_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchLogResponse(BaseModel):
    """Schema for search log response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    query: str
    results_count: int
    avg_score: Optional[float]
    metadata: Dict[str, Any]
    created_at: datetime
